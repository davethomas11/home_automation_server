"""
/pairing router – initiate and complete Apple TV pairing.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from home_automation_server.db.session import get_session
from home_automation_server.models.models import (
    AppleTVDevice,
    AppleTVPairing,
    AppleTVPairingRead,
)
from home_automation_server.services import pyatv_service

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class StartPairingRequest(BaseModel):
    device_id: int
    protocol: str  # "MRP" | "Companion" | "AirPlay"


class FinishPairingRequest(BaseModel):
    device_id: int
    protocol: str
    pin: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/start", summary="Start pairing with a device")
async def start_pairing(body: StartPairingRequest, session: SessionDep):
    """Begins the pairing flow and returns instructions for entering the PIN."""
    device = session.get(AppleTVDevice, body.device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    try:
        message = await pyatv_service.start_pairing(
            device.identifier, device.ip_address, body.protocol
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"status": "pairing_started", "message": message, "protocol": body.protocol}


@router.post("/finish", response_model=AppleTVPairingRead, summary="Finish pairing and save credentials")
async def finish_pairing(body: FinishPairingRequest, session: SessionDep):
    """Submits the PIN, finalises pairing, and stores credentials in the database."""
    device = session.get(AppleTVDevice, body.device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    try:
        credentials = await pyatv_service.finish_pairing(
            device.identifier, body.protocol, body.pin
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # Upsert: replace existing credentials for same device/protocol
    existing = session.exec(
        select(AppleTVPairing)
        .where(AppleTVPairing.device_id == body.device_id)
        .where(AppleTVPairing.protocol == body.protocol)
    ).first()

    if existing:
        existing.credentials = credentials
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    pairing = AppleTVPairing(
        device_id=body.device_id,
        protocol=body.protocol,
        credentials=credentials,
    )
    session.add(pairing)
    session.commit()
    session.refresh(pairing)
    return pairing


@router.get("/{device_id}", response_model=list[AppleTVPairingRead], summary="List credentials for a device")
def list_pairings(device_id: int, session: SessionDep):
    return session.exec(
        select(AppleTVPairing).where(AppleTVPairing.device_id == device_id)
    ).all()


@router.delete("/{pairing_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a pairing record")
def delete_pairing(pairing_id: int, session: SessionDep):
    pairing = session.get(AppleTVPairing, pairing_id)
    if not pairing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pairing not found")
    session.delete(pairing)
    session.commit()

