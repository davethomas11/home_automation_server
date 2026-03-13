"""
/controls router – send remote and power controls to saved Apple TV devices.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from home_automation_server.db.session import get_session
from home_automation_server.models.models import AppleTVDevice, AppleTVPairing, DeviceKind
from home_automation_server.services import pyatv_service
from home_automation_server.services.provider_resolver import (
    ProviderResolutionError,
    resolve_provider,
)

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]


class RemoteCommandRequest(BaseModel):
    device_id: int
    command: str


class PowerRequest(BaseModel):
    device_id: int
    turn_on: bool


class KindRemoteCommandRequest(BaseModel):
    device_kind: DeviceKind
    device_id: int
    command: str


class KindPowerRequest(BaseModel):
    device_kind: DeviceKind
    device_id: int
    turn_on: bool


def _get_device_and_credentials(device_id: int, session: SessionDep) -> tuple[AppleTVDevice, dict[str, str]]:
    device = session.get(AppleTVDevice, device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    pairings = session.exec(
        select(AppleTVPairing).where(AppleTVPairing.device_id == device_id)
    ).all()
    credentials = {p.protocol: p.credentials for p in pairings}

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No saved credentials for this device. Pair first.",
        )

    return device, credentials


async def _send_command_with_kind(kind: DeviceKind, device_id: int, command: str, session: SessionDep):
    try:
        resolved = resolve_provider(kind, device_id, session)
    except ProviderResolutionError as exc:
        message = str(exc)
        if "pair first" in message.lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)

    try:
        await resolved.provider.send_command(command)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return {
        "status": "ok",
        "device": resolved.device_name,
        "device_kind": kind.value,
        "command": command,
    }


async def _send_power_with_kind(kind: DeviceKind, device_id: int, turn_on: bool, session: SessionDep):
    try:
        resolved = resolve_provider(kind, device_id, session)
    except ProviderResolutionError as exc:
        message = str(exc)
        if "pair first" in message.lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)

    try:
        await resolved.provider.power(turn_on)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return {
        "status": "ok",
        "device": resolved.device_name,
        "device_kind": kind.value,
        "power": "on" if turn_on else "off",
    }


@router.get("/commands", summary="List supported remote commands")
def list_commands():
    return sorted(pyatv_service.REMOTE_COMMAND_MAP.keys())


@router.post("/command", summary="Send a remote command")
async def send_command(body: RemoteCommandRequest, session: SessionDep):
    device, credentials = _get_device_and_credentials(body.device_id, session)

    try:
        await pyatv_service.send_remote_command(
            device.identifier,
            device.ip_address,
            credentials,
            body.command,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return {"status": "ok", "device": device.name, "command": body.command}


@router.post("/appletv/command", summary="Send a remote command to an Apple TV")
async def send_command_appletv(body: RemoteCommandRequest, session: SessionDep):
    return await _send_command_with_kind(DeviceKind.APPLE_TV, body.device_id, body.command, session)


@router.post("/samsung/command", summary="Send a remote command to a Samsung TV")
async def send_command_samsung(body: RemoteCommandRequest, session: SessionDep):
    return await _send_command_with_kind(DeviceKind.SAMSUNG_TV, body.device_id, body.command, session)


@router.post("/command/by-kind", summary="Send a remote command to a device by kind")
async def send_command_by_kind(body: KindRemoteCommandRequest, session: SessionDep):
    return await _send_command_with_kind(body.device_kind, body.device_id, body.command, session)


@router.post("/power", summary="Turn a device on or off")
async def send_power(body: PowerRequest, session: SessionDep):
    device, credentials = _get_device_and_credentials(body.device_id, session)

    try:
        await pyatv_service.power_toggle(
            device.identifier,
            device.ip_address,
            credentials,
            body.turn_on,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return {
        "status": "ok",
        "device": device.name,
        "power": "on" if body.turn_on else "off",
    }


@router.post("/appletv/power", summary="Turn an Apple TV on or off")
async def send_power_appletv(body: PowerRequest, session: SessionDep):
    return await _send_power_with_kind(DeviceKind.APPLE_TV, body.device_id, body.turn_on, session)


@router.post("/samsung/power", summary="Turn a Samsung TV on or off")
async def send_power_samsung(body: PowerRequest, session: SessionDep):
    return await _send_power_with_kind(DeviceKind.SAMSUNG_TV, body.device_id, body.turn_on, session)


# The Samsung WebSocket API is a one-way command channel — it cannot query the TV for live
# input state. Input switching support is tiered by model generation:
#   - KEY_SOURCE / KEY_HDMI  → universally supported (open picker / cycle HDMI)
#   - KEY_HDMI1-4 etc.       → pre-2016 / some mid-range models only; Tizen 2016+ ignores them
#   - Named direct switching → SmartThings cloud API only (not implemented here)
_SAMSUNG_INPUTS = [
    {
        "label": "Source Menu",
        "command": "source",
        "icon": "⬡",
        "tier": "universal",
        "note": "Opens on-screen input picker — works on all models",
    },
    {
        "label": "HDMI Cycle",
        "command": "hdmi_cycle",
        "icon": "🔄",
        "tier": "universal",
        "note": "Cycles through HDMI inputs — works on most models",
    },
    {
        "label": "HDMI 1",
        "command": "hdmi_1",
        "icon": "🔌",
        "tier": "model_dependent",
        "note": "Direct switch — pre-2016 models and some mid-range; not supported on most Tizen TVs",
    },
    {
        "label": "HDMI 2",
        "command": "hdmi_2",
        "icon": "🔌",
        "tier": "model_dependent",
        "note": "Direct switch — pre-2016 models and some mid-range; not supported on most Tizen TVs",
    },
    {
        "label": "HDMI 3",
        "command": "hdmi_3",
        "icon": "🔌",
        "tier": "model_dependent",
        "note": "Direct switch — pre-2016 models and some mid-range; not supported on most Tizen TVs",
    },
    {
        "label": "HDMI 4",
        "command": "hdmi_4",
        "icon": "🔌",
        "tier": "model_dependent",
        "note": "Direct switch — pre-2016 models and some mid-range; not supported on most Tizen TVs",
    },
    {
        "label": "AV",
        "command": "av_1",
        "icon": "📺",
        "tier": "model_dependent",
        "note": "Composite AV input — model dependent",
    },
    {
        "label": "Component",
        "command": "component_1",
        "icon": "📺",
        "tier": "model_dependent",
        "note": "Component input — model dependent",
    },
    {
        "label": "PC",
        "command": "pc",
        "icon": "💻",
        "tier": "model_dependent",
        "note": "PC/DVI input — model dependent",
    },
]


@router.get(
    "/samsung/sources/{device_id}",
    summary="List switchable inputs for a Samsung TV",
)
async def get_samsung_sources(device_id: int, session: SessionDep):
    """
    Returns the known inputs for a Samsung TV, grouped by how reliably they can be
    switched to via the local WebSocket API.

    **Tiers:**
    - `universal` — works on all models (open source picker / HDMI cycle)
    - `model_dependent` — direct KEY_HDMI1 etc.; only honoured on pre-2016 and some
      mid-range models. Most Tizen 2016+ TVs silently ignore these keys.
    - `smartthings_only` — true named-input switching requires the SmartThings cloud API

    **Important:** The Samsung WebSocket API is write-only. It cannot report which
    devices are physically connected or which input is currently active.
    """
    from home_automation_server.models.models import SamsungTVDevice
    device = session.get(SamsungTVDevice, device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Samsung TV device not found")

    return {
        "device_id": device_id,
        "device_name": device.name,
        "model_year": device.model_year,
        "live_enumeration_supported": False,
        "direct_switch_supported": device.model_year is not None and device.model_year < 2016,
        "note": (
            "The Samsung WebSocket API is write-only. "
            "Direct input switching (KEY_HDMI1 etc.) only works on pre-2016 Samsung models. "
            "For Tizen 2016+ TVs use 'Source Menu' or 'HDMI Cycle'. "
            "True named-input switching on modern TVs requires the SmartThings cloud API."
        ),
        "inputs": _SAMSUNG_INPUTS,
    }


@router.post("/power/by-kind", summary="Turn a device on or off by kind")
async def send_power_by_kind(body: KindPowerRequest, session: SessionDep):
    return await _send_power_with_kind(body.device_kind, body.device_id, body.turn_on, session)


@router.get("/power-state/{device_id}", summary="Get current power state")
async def get_power_state(device_id: int, session: SessionDep):
    device, credentials = _get_device_and_credentials(device_id, session)

    try:
        power = await pyatv_service.get_power_state(
            device.identifier,
            device.ip_address,
            credentials,
        )
    except RuntimeError as exc:
        message = str(exc)
        if "not supported" in message.lower():
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=message)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=message)

    return {
        "status": "ok",
        "device": device.name,
        "power_state": power["state"],
        "is_on": power["is_on"],
    }


