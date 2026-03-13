"""
/devices router – scan for and manage Apple TV devices.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from home_automation_server.db.session import get_session
from home_automation_server.models.models import (
    AppleTVDevice,
    AppleTVDeviceCreate,
    AppleTVDeviceRead,
    AppleTVPairing,
    SamsungTVDevice,
    SamsungTVDeviceCreate,
    SamsungTVDeviceRead,
)
from home_automation_server.services import pyatv_service
from home_automation_server.services import samsungtv_service

router = APIRouter()
logger = logging.getLogger(__name__)

SessionDep = Annotated[Session, Depends(get_session)]


class DeviceBatchSaveRequest(BaseModel):
    devices: list[AppleTVDeviceCreate]


class SamsungDeviceBatchSaveRequest(BaseModel):
    devices: list[SamsungTVDeviceCreate]


class SamsungPairRequest(BaseModel):
    token: str | None = None


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

@router.post("/scan", summary="Scan local network for Apple TVs")
async def scan_devices():
    """
    Scan the local network for Apple TV devices using pyatv.
    Returns a list of discovered devices (not persisted automatically).
    
    Note: This includes devices with AirPlay support. Samsung TVs with AirPlay
    should be filtered in the UI and managed via /devices/samsung/scan for proper
    WebSocket control.
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


@router.post("/samsung/scan", summary="Scan local network for Samsung TVs")
async def scan_samsung_devices():
    """
    Scan for Samsung TVs, using AirPlay-discovered devices to optimize IP detection.
    """
    # First get AirPlay devices to pass as hints for faster Samsung TV discovery
    airplay_devices = []
    try:
        airplay_discovered = await pyatv_service.scan_for_devices()
        airplay_devices = [
            {"name": d.name, "ip_address": d.ip_address}
            for d in airplay_discovered
        ]
    except Exception:
        logger.debug("AirPlay scan did not provide device hints, proceeding with standard Samsung scan")

    try:
        devices = await samsungtv_service.scan_for_samsung_devices_with_airplay(
            airplay_devices=airplay_devices
        )
    except samsungtv_service.SamsungTVError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return [
        {
            "name": d.name,
            "ip_address": d.ip_address,
            "model": d.model,
            "model_year": d.model_year,
            "port": d.port,
        }
        for d in devices
    ]


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[AppleTVDeviceRead], summary="List saved devices")
def list_devices(session: SessionDep):
    return session.exec(select(AppleTVDevice)).all()


@router.get("/appletv", response_model=list[AppleTVDeviceRead], summary="List saved Apple TVs")
def list_appletv_devices(session: SessionDep):
    return session.exec(select(AppleTVDevice)).all()


@router.get("/samsung", response_model=list[SamsungTVDeviceRead], summary="List saved Samsung TVs")
def list_samsung_devices(session: SessionDep):
    return session.exec(select(SamsungTVDevice)).all()


@router.get("/samsung/{device_id}", response_model=SamsungTVDeviceRead, summary="Get a Samsung TV")
def get_samsung_device(device_id: int, session: SessionDep):
    device = session.get(SamsungTVDevice, device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Samsung TV device not found")
    return device


@router.get("/{device_id}", response_model=AppleTVDeviceRead, summary="Get a device")
def get_device(device_id: int, session: SessionDep):
    device = session.get(AppleTVDevice, device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


@router.get("/appletv/{device_id}", response_model=AppleTVDeviceRead, summary="Get an Apple TV")
def get_appletv_device(device_id: int, session: SessionDep):
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


@router.post(
    "/appletv",
    response_model=AppleTVDeviceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Save an Apple TV",
)
def create_appletv_device(device_in: AppleTVDeviceCreate, session: SessionDep):
    device = AppleTVDevice.model_validate(device_in)
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


@router.post(
    "/samsung",
    response_model=SamsungTVDeviceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Save a Samsung TV",
)
def create_samsung_device(device_in: SamsungTVDeviceCreate, session: SessionDep):
    device = SamsungTVDevice.model_validate(device_in)
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


@router.post("/appletv/batch", summary="Save multiple Apple TVs and skip existing ones")
def create_appletv_devices_batch(body: DeviceBatchSaveRequest, session: SessionDep):
    return create_devices_batch(body, session)


@router.post("/samsung/batch", summary="Save multiple Samsung TVs and skip existing ones")
def create_samsung_devices_batch(body: SamsungDeviceBatchSaveRequest, session: SessionDep):
    """
    Save multiple Samsung TVs at once.
    Devices with the same IP+port combination are skipped.
    """
    added: list[dict] = []
    skipped: list[dict] = []

    for device_in in body.devices:
        existing = session.exec(
            select(SamsungTVDevice).where(
                SamsungTVDevice.ip_address == device_in.ip_address,
                SamsungTVDevice.port == device_in.port,
            )
        ).first()

        if existing:
            skipped.append(
                {
                    "id": existing.id,
                    "name": existing.name,
                    "ip_address": existing.ip_address,
                    "port": existing.port,
                    "reason": "already_saved",
                }
            )
            continue

        device = SamsungTVDevice.model_validate(device_in)
        session.add(device)
        session.commit()
        session.refresh(device)
        added.append(
            {
                "id": device.id,
                "name": device.name,
                "ip_address": device.ip_address,
                "port": device.port,
                "model_year": device.model_year,
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
    
    # Delete associated pairings first (cascade)
    pairings = session.exec(
        select(AppleTVPairing).where(AppleTVPairing.device_id == device_id)
    ).all()
    for pairing in pairings:
        session.delete(pairing)
    
    session.delete(device)
    session.commit()


@router.delete("/appletv/{device_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an Apple TV")
def delete_appletv_device(device_id: int, session: SessionDep):
    device = session.get(AppleTVDevice, device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    
    # Delete associated pairings first (cascade)
    pairings = session.exec(
        select(AppleTVPairing).where(AppleTVPairing.device_id == device_id)
    ).all()
    for pairing in pairings:
        session.delete(pairing)
    
    session.delete(device)
    session.commit()


@router.delete("/samsung/{device_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a Samsung TV")
def delete_samsung_device(device_id: int, session: SessionDep):
    device = session.get(SamsungTVDevice, device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Samsung TV device not found")
    session.delete(device)
    session.commit()


@router.post("/samsung/{device_id}/pair", summary="Perform Samsung TV pairing/auth handshake")
async def pair_samsung_device(device_id: int, body: SamsungPairRequest, session: SessionDep):
    device = session.get(SamsungTVDevice, device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Samsung TV device not found")

    token_for_handshake = body.token if body.token is not None else device.token

    try:
        new_token = await samsungtv_service.pair_samsung_device(
            ip_address=device.ip_address,
            port=device.port,
            token=token_for_handshake,
        )
    except samsungtv_service.SamsungTVError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    token_saved = False
    if new_token and new_token != device.token:
        device.token = new_token
        session.add(device)
        session.commit()
        session.refresh(device)
        token_saved = True

    return {
        "status": "ok",
        "device": device.name,
        "paired": True,
        "token_saved": token_saved,
        "has_token": bool(device.token),
    }


