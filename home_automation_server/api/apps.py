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
)
from home_automation_server.services import pyatv_service

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]


class LaunchRequest(BaseModel):
    device_id: int
    bundle_id: str


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

