"""
/ui router – Jinja2 template-rendered pages.
"""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from home_automation_server.db.session import get_session
from home_automation_server.models.models import (
    AppleTVDevice,
    AppleTVPairing,
    AutomationFlow,
    AppLaunchConfig,
    DeviceKind,
    SamsungTVDevice,
)

router = APIRouter()
templates = Jinja2Templates(directory="home_automation_server/frontend/templates")

SessionDep = Annotated[Session, Depends(get_session)]


def _controls_route(kind: DeviceKind, device_id: int) -> str:
    return f"/ui/controls/{kind.value}/{device_id}"


def _build_controls_devices(session: Session) -> tuple[list[AppleTVDevice], list[SamsungTVDevice], list[dict[str, object]]]:
    atv_devices = session.exec(select(AppleTVDevice)).all()
    samsung_devices = session.exec(select(SamsungTVDevice)).all()

    controls_devices: list[dict[str, object]] = [
        {
            "kind": DeviceKind.APPLE_TV.value,
            "kind_label": "Apple TV",
            "id": d.id,
            "name": d.name,
            "ip_address": d.ip_address,
            "route": _controls_route(DeviceKind.APPLE_TV, d.id),
        }
        for d in atv_devices
        if d.id is not None
    ] + [
        {
            "kind": DeviceKind.SAMSUNG_TV.value,
            "kind_label": "Samsung TV",
            "id": d.id,
            "name": d.name,
            "ip_address": d.ip_address,
            "route": _controls_route(DeviceKind.SAMSUNG_TV, d.id),
        }
        for d in samsung_devices
        if d.id is not None
    ]

    return atv_devices, samsung_devices, controls_devices


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def ui_index(request: Request, session: SessionDep):
    devices = session.exec(select(AppleTVDevice)).all()
    return templates.TemplateResponse(
        request, "index.html", {"request": request, "devices": devices}
    )


@router.get("/devices", response_class=HTMLResponse, include_in_schema=False)
def ui_devices(request: Request, session: SessionDep):
    devices = session.exec(select(AppleTVDevice)).all()
    samsung_devices = session.exec(select(SamsungTVDevice)).all()
    pairings = session.exec(select(AppleTVPairing)).all()
    # Build device_id → list[protocol] so the template knows which protocols are paired
    pairing_protocols: dict[int, list[str]] = {}
    for p in pairings:
        pairing_protocols.setdefault(p.device_id, []).append(p.protocol)
    return templates.TemplateResponse(
        request,
        "devices.html",
        {
            "request": request,
            "devices": devices,
            "samsung_devices": samsung_devices,
            "pairing_protocols": pairing_protocols,
        },
    )


@router.get("/pairing", response_class=HTMLResponse, include_in_schema=False)
def ui_pairing(request: Request, session: SessionDep, device_id: int | None = None):
    devices = session.exec(select(AppleTVDevice)).all()
    pairings = session.exec(select(AppleTVPairing)).all()
    # Build a mapping device_id → list of pairings
    pairing_map: dict[int, list] = {}
    for p in pairings:
        pairing_map.setdefault(p.device_id, []).append(p)
    return templates.TemplateResponse(
        request,
        "pairing.html",
        {
            "request": request,
            "devices": devices,
            "pairing_map": pairing_map,
            "preselect_device_id": device_id,
        },
    )


@router.get("/automations", response_class=HTMLResponse, include_in_schema=False)
def ui_automations(request: Request, session: SessionDep):
    flows = session.exec(select(AutomationFlow)).all()
    apple_devices = session.exec(select(AppleTVDevice)).all()
    samsung_devices = session.exec(select(SamsungTVDevice)).all()

    automation_devices: list[dict[str, object]] = [
        {"kind": "apple_tv", "id": d.id, "name": d.name, "ip_address": d.ip_address}
        for d in apple_devices
    ] + [
        {"kind": "samsung_tv", "id": d.id, "name": d.name, "ip_address": d.ip_address}
        for d in samsung_devices
    ]

    device_map: dict[str, dict[str, object]] = {
        f"apple_tv:{d.id}": {"name": d.name, "kind": "apple_tv", "ip_address": d.ip_address}
        for d in apple_devices
    }
    device_map.update(
        {
            f"samsung_tv:{d.id}": {"name": d.name, "kind": "samsung_tv", "ip_address": d.ip_address}
            for d in samsung_devices
        }
    )

    return templates.TemplateResponse(
        request,
        "automations.html",
        {
            "request": request,
            "flows": flows,
            "automation_devices": automation_devices,
            "automation_devices_json": json.dumps(automation_devices),
            "device_map": device_map,
        },
    )


@router.get("/apps", response_class=HTMLResponse, include_in_schema=False)
def ui_apps(request: Request, session: SessionDep):
    configs = session.exec(select(AppLaunchConfig)).all()
    devices = session.exec(select(AppleTVDevice)).all()
    device_map = {d.id: d for d in devices}
    return templates.TemplateResponse(
        request,
        "apps.html",
        {"request": request, "configs": configs, "devices": devices, "device_map": device_map},
    )


@router.get("/controls", response_class=HTMLResponse, include_in_schema=False)
def ui_controls(request: Request, session: SessionDep):
    atv_devices, samsung_devices, controls_devices = _build_controls_devices(session)
    if controls_devices:
        return RedirectResponse(url=str(controls_devices[0]["route"]), status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        request,
        "controls.html",
        {
            "request": request,
            "atv_devices": atv_devices,
            "samsung_devices": samsung_devices,
            "controls_devices": controls_devices,
            "selected_device": None,
            "selected_device_kind": None,
        },
    )


@router.get("/controls/{device_kind}/{device_id}", response_class=HTMLResponse, include_in_schema=False)
def ui_controls_device(request: Request, device_kind: DeviceKind, device_id: int, session: SessionDep):
    atv_devices, samsung_devices, controls_devices = _build_controls_devices(session)

    if device_kind == DeviceKind.APPLE_TV:
        selected_device = session.get(AppleTVDevice, device_id)
        if not selected_device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Apple TV device not found")
    elif device_kind == DeviceKind.SAMSUNG_TV:
        selected_device = session.get(SamsungTVDevice, device_id)
        if not selected_device:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Samsung TV device not found")
    else:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unsupported device kind")

    for device in controls_devices:
        device["is_selected"] = (
            device["kind"] == device_kind.value and device["id"] == device_id
        )

    return templates.TemplateResponse(
        request,
        "controls.html",
        {
            "request": request,
            "atv_devices": atv_devices,
            "samsung_devices": samsung_devices,
            "controls_devices": controls_devices,
            "selected_device": selected_device,
            "selected_device_kind": device_kind.value,
        },
    )


