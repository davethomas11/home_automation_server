"""
/controls router – send remote and power controls to saved Apple TV devices.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from home_automation_server.db.session import get_session
from home_automation_server.models.models import AppleTVDevice, AppleTVPairing
from home_automation_server.services import pyatv_service

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]


class RemoteCommandRequest(BaseModel):
    device_id: int
    command: str


class PowerRequest(BaseModel):
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


