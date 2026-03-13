"""
/apps router – manage AppLaunchConfig records and launch apps.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from home_automation_server.db.session import get_session
from home_automation_server.models.models import (
    AppLaunchConfig,
    AppLaunchConfigCreate,
    AppLaunchConfigRead,
    AppleTVDevice,
    AppleTVPairing,
    DeviceKind,
)
from home_automation_server.services import pyatv_service
from home_automation_server.services.provider_resolver import (
    ProviderResolutionError,
    resolve_provider,
)

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]


class LaunchRequest(BaseModel):
    device_id: int
    bundle_id: str


class SamsungLaunchRequest(BaseModel):
    device_id: int
    app_id: str


class KindLaunchRequest(BaseModel):
    device_kind: DeviceKind
    device_id: int
    app_id: str


# ---------------------------------------------------------------------------
# AppLaunchConfig CRUD
# ---------------------------------------------------------------------------

@router.get("/configs", response_model=list[AppLaunchConfigRead], summary="List app launch configs")
def list_configs(session: SessionDep):
    return session.exec(select(AppLaunchConfig)).all()


@router.post(
    "/configs",
    response_model=AppLaunchConfigRead,
    status_code=status.HTTP_201_CREATED,
    summary="Save an app launch config",
)
def create_config(config_in: AppLaunchConfigCreate, session: SessionDep):
    config = AppLaunchConfig.model_validate(config_in)
    session.add(config)
    session.commit()
    session.refresh(config)
    return config


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a config")
def delete_config(config_id: int, session: SessionDep):
    config = session.get(AppLaunchConfig, config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")
    session.delete(config)
    session.commit()


# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------

@router.post("/launch", summary="Launch an app on an Apple TV")
async def launch_app(body: LaunchRequest, session: SessionDep):
    """Launch an app by bundle ID on the specified device."""
    device = session.get(AppleTVDevice, body.device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    pairings = session.exec(
        select(AppleTVPairing).where(AppleTVPairing.device_id == body.device_id)
    ).all()
    credentials = {p.protocol: p.credentials for p in pairings}

    try:
        await pyatv_service.launch_app(
            device.identifier, device.ip_address, credentials, body.bundle_id
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return {"status": "ok", "bundle_id": body.bundle_id, "device": device.name}


async def _launch_with_kind(kind: DeviceKind, device_id: int, app_id: str, session: SessionDep):
    try:
        resolved = resolve_provider(kind, device_id, session)
    except ProviderResolutionError as exc:
        message = str(exc)
        if "pair first" in message.lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)

    try:
        await resolved.provider.launch_app(app_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return {
        "status": "ok",
        "app_id": app_id,
        "device": resolved.device_name,
        "device_kind": kind.value,
    }


@router.post("/appletv/launch", summary="Launch an app on an Apple TV")
async def launch_app_appletv(body: LaunchRequest, session: SessionDep):
    return await _launch_with_kind(DeviceKind.APPLE_TV, body.device_id, body.bundle_id, session)


@router.post("/samsung/launch", summary="Launch an app on a Samsung TV")
async def launch_app_samsung(body: SamsungLaunchRequest, session: SessionDep):
    return await _launch_with_kind(DeviceKind.SAMSUNG_TV, body.device_id, body.app_id, session)


@router.post("/launch/by-kind", summary="Launch an app by device kind")
async def launch_app_by_kind(body: KindLaunchRequest, session: SessionDep):
    return await _launch_with_kind(body.device_kind, body.device_id, body.app_id, session)


@router.post("/device/{device_kind}/{device_id}/launch/{app_id}", summary="Launch app by kind and device path")
async def launch_app_by_path(device_kind: DeviceKind, device_id: int, app_id: str, session: SessionDep):
    return await _launch_with_kind(device_kind, device_id, app_id, session)


@router.get("/list/{device_id}", summary="List installed apps on a device")
async def list_installed_apps(device_id: int, session: SessionDep):
    """Fetch the list of installed apps from the Apple TV."""
    device = session.get(AppleTVDevice, device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    pairings = session.exec(
        select(AppleTVPairing).where(AppleTVPairing.device_id == device_id)
    ).all()
    credentials = {p.protocol: p.credentials for p in pairings}

    try:
        apps = await pyatv_service.list_apps(device.identifier, device.ip_address, credentials)
    except RuntimeError as exc:
        message = str(exc)
        if "not supported" in message.lower():
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=message)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=message)

    return apps

