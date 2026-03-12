"""
/ui router – Jinja2 template-rendered pages.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from home_automation_server.db.session import get_session
from home_automation_server.models.models import (
    AppleTVDevice,
    AppleTVPairing,
    AutomationFlow,
    AppLaunchConfig,
)

router = APIRouter()
templates = Jinja2Templates(directory="home_automation_server/frontend/templates")

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def ui_index(request: Request, session: SessionDep):
    devices = session.exec(select(AppleTVDevice)).all()
    return templates.TemplateResponse(
        "index.html", {"request": request, "devices": devices}
    )


@router.get("/devices", response_class=HTMLResponse, include_in_schema=False)
def ui_devices(request: Request, session: SessionDep):
    devices = session.exec(select(AppleTVDevice)).all()
    return templates.TemplateResponse(
        "devices.html", {"request": request, "devices": devices}
    )


@router.get("/pairing", response_class=HTMLResponse, include_in_schema=False)
def ui_pairing(request: Request, session: SessionDep):
    devices = session.exec(select(AppleTVDevice)).all()
    pairings = session.exec(select(AppleTVPairing)).all()
    # Build a mapping device_id → list of pairings
    pairing_map: dict[int, list] = {}
    for p in pairings:
        pairing_map.setdefault(p.device_id, []).append(p)
    return templates.TemplateResponse(
        "pairing.html",
        {"request": request, "devices": devices, "pairing_map": pairing_map},
    )


@router.get("/automations", response_class=HTMLResponse, include_in_schema=False)
def ui_automations(request: Request, session: SessionDep):
    flows = session.exec(select(AutomationFlow)).all()
    devices = session.exec(select(AppleTVDevice)).all()
    device_map = {d.id: d for d in devices}
    return templates.TemplateResponse(
        "automations.html",
        {"request": request, "flows": flows, "devices": devices, "device_map": device_map},
    )


@router.get("/apps", response_class=HTMLResponse, include_in_schema=False)
def ui_apps(request: Request, session: SessionDep):
    configs = session.exec(select(AppLaunchConfig)).all()
    devices = session.exec(select(AppleTVDevice)).all()
    device_map = {d.id: d for d in devices}
    return templates.TemplateResponse(
        "apps.html",
        {"request": request, "configs": configs, "devices": devices, "device_map": device_map},
    )


@router.get("/controls", response_class=HTMLResponse, include_in_schema=False)
def ui_controls(request: Request, session: SessionDep):
    devices = session.exec(select(AppleTVDevice)).all()
    return templates.TemplateResponse(
        "controls.html",
        {"request": request, "devices": devices},
    )


