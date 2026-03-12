"""
/devices router – scan for and manage Apple TV devices.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from home_automation_server.db.session import get_session
from home_automation_server.models.models import (
    AppleTVDevice,
    AppleTVDeviceCreate,
    AppleTVDeviceRead,
)
from home_automation_server.services import pyatv_service

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]


class DeviceBatchSaveRequest(BaseModel):
    devices: list[AppleTVDeviceCreate]


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

@router.post("/scan", summary="Scan local network for Apple TVs")
async def scan_devices():
    """
    Scan the local network for Apple TV devices using pyatv.
    Returns a list of discovered devices (not persisted automatically).
    """
    devices = await pyatv_service.scan_for_devices()
    return [
        {
            "name": d.name,
            "identifier": d.identifier,
            "ip_address": d.ip_address,
            "model": d.model,
            "os_version": d.os_version,
        }
        for d in devices
    ]


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[AppleTVDeviceRead], summary="List saved devices")
def list_devices(session: SessionDep):
    return session.exec(select(AppleTVDevice)).all()


@router.get("/{device_id}", response_model=AppleTVDeviceRead, summary="Get a device")
def get_device(device_id: int, session: SessionDep):
    device = session.get(AppleTVDevice, device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


@router.post("/", response_model=AppleTVDeviceRead, status_code=status.HTTP_201_CREATED, summary="Save a device")
def create_device(device_in: AppleTVDeviceCreate, session: SessionDep):
    device = AppleTVDevice.model_validate(device_in)
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


@router.post("/batch", summary="Save multiple devices and skip existing ones")
def create_devices_batch(body: DeviceBatchSaveRequest, session: SessionDep):
    """
    Save multiple devices at once.
    Devices with an identifier that already exists are skipped.
    """
    added: list[dict] = []
    skipped: list[dict] = []

    for device_in in body.devices:
        existing = session.exec(
            select(AppleTVDevice).where(AppleTVDevice.identifier == device_in.identifier)
        ).first()

        if existing:
            skipped.append(
                {
                    "id": existing.id,
                    "name": existing.name,
                    "identifier": existing.identifier,
                    "ip_address": existing.ip_address,
                    "reason": "already_saved",
                }
            )
            continue

        device = AppleTVDevice.model_validate(device_in)
        session.add(device)
        session.commit()
        session.refresh(device)
        added.append(
            {
                "id": device.id,
                "name": device.name,
                "identifier": device.identifier,
                "ip_address": device.ip_address,
            }
        )

    return {
        "added_count": len(added),
        "skipped_count": len(skipped),
        "added": added,
        "skipped": skipped,
    }


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a device")
def delete_device(device_id: int, session: SessionDep):
    device = session.get(AppleTVDevice, device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    session.delete(device)
    session.commit()

