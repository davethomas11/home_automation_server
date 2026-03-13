"""
/automations router – manage and execute automation flows.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from home_automation_server.db.session import get_session
from home_automation_server.models.models import (
    AutomationFlow,
    AutomationFlowCreate,
    AutomationFlowRead,
    DeviceKind,
)
from home_automation_server.services.automation_events import broker as automation_event_broker, make_event
from home_automation_server.services.automation_engine import execute_flow

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]


def _sse(event_name: str, payload: dict) -> str:
    data = json.dumps(payload, separators=(",", ":"))
    return f"event: {event_name}\ndata: {data}\n\n"


@router.get("/", response_model=list[AutomationFlowRead], summary="List all automation flows")
def list_flows(session: SessionDep):
    return session.exec(select(AutomationFlow)).all()


@router.get("/appletv", response_model=list[AutomationFlowRead], summary="List Apple TV automation flows")
def list_appletv_flows(session: SessionDep):
    return session.exec(
        select(AutomationFlow).where(AutomationFlow.device_kind == DeviceKind.APPLE_TV)
    ).all()


@router.get("/samsung", response_model=list[AutomationFlowRead], summary="List Samsung TV automation flows")
def list_samsung_flows(session: SessionDep):
    return session.exec(
        select(AutomationFlow).where(AutomationFlow.device_kind == DeviceKind.SAMSUNG_TV)
    ).all()


@router.get("/{flow_id}", response_model=AutomationFlowRead, summary="Get a flow")
def get_flow(flow_id: int, session: SessionDep):
    flow = session.get(AutomationFlow, flow_id)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")
    return flow


@router.post(
    "/",
    response_model=AutomationFlowRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an automation flow",
)
def create_flow(flow_in: AutomationFlowCreate, session: SessionDep):
    flow = AutomationFlow.model_validate(flow_in)
    session.add(flow)
    session.commit()
    session.refresh(flow)
    return flow


@router.post(
    "/appletv",
    response_model=AutomationFlowRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an Apple TV automation flow",
)
def create_appletv_flow(flow_in: AutomationFlowCreate, session: SessionDep):
    payload = flow_in.model_dump()
    payload["device_kind"] = DeviceKind.APPLE_TV
    flow = AutomationFlow.model_validate(payload)
    session.add(flow)
    session.commit()
    session.refresh(flow)
    return flow


@router.post(
    "/samsung",
    response_model=AutomationFlowRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Samsung TV automation flow",
)
def create_samsung_flow(flow_in: AutomationFlowCreate, session: SessionDep):
    payload = flow_in.model_dump()
    payload["device_kind"] = DeviceKind.SAMSUNG_TV
    flow = AutomationFlow.model_validate(payload)
    session.add(flow)
    session.commit()
    session.refresh(flow)
    return flow


@router.put("/{flow_id}", response_model=AutomationFlowRead, summary="Update a flow")
def update_flow(flow_id: int, flow_in: AutomationFlowCreate, session: SessionDep):
    flow = session.get(AutomationFlow, flow_id)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")
    flow_data = flow_in.model_dump(exclude_unset=True)
    for key, value in flow_data.items():
        setattr(flow, key, value)
    session.add(flow)
    session.commit()
    session.refresh(flow)
    return flow


@router.put("/appletv/{flow_id}", response_model=AutomationFlowRead, summary="Update an Apple TV flow")
def update_appletv_flow(flow_id: int, flow_in: AutomationFlowCreate, session: SessionDep):
    payload = flow_in.model_dump()
    payload["device_kind"] = DeviceKind.APPLE_TV
    return update_flow(flow_id, AutomationFlowCreate.model_validate(payload), session)


@router.put("/samsung/{flow_id}", response_model=AutomationFlowRead, summary="Update a Samsung TV flow")
def update_samsung_flow(flow_id: int, flow_in: AutomationFlowCreate, session: SessionDep):
    payload = flow_in.model_dump()
    payload["device_kind"] = DeviceKind.SAMSUNG_TV
    return update_flow(flow_id, AutomationFlowCreate.model_validate(payload), session)


@router.delete("/{flow_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a flow")
def delete_flow(flow_id: int, session: SessionDep):
    flow = session.get(AutomationFlow, flow_id)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")
    session.delete(flow)
    session.commit()


@router.post("/{flow_id}/run", summary="Manually trigger a flow")
async def run_flow(flow_id: int, session: SessionDep, run_id: str | None = None):
    """Execute a flow immediately (manual trigger)."""
    try:
        result = await execute_flow(flow_id, session, run_id=run_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    return result


@router.get("/{flow_id}/events", summary="Stream automation execution events (SSE)")
async def flow_events(flow_id: int, session: SessionDep, run_id: str | None = None, timeout_seconds: float = 60.0):
    flow = session.get(AutomationFlow, flow_id)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")

    async def event_stream():
        deadline = time.monotonic() + max(1.0, timeout_seconds)
        queue = await automation_event_broker.subscribe(flow_id)
        try:
            yield _sse(
                "connected",
                make_event("connected", flow_id=flow_id, run_id=run_id or "", timeout_seconds=timeout_seconds),
            )

            # Replay recent events so clients that connect slightly late still sync correctly.
            history = await automation_event_broker.get_history(flow_id, run_id=run_id)
            for message in history:
                yield _sse(str(message.get("type") or "message"), message)

            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=min(10.0, remaining))
                except TimeoutError:
                    yield _sse(
                        "keepalive",
                        make_event("keepalive", flow_id=flow_id, run_id=run_id or ""),
                    )
                    continue

                if run_id and message.get("run_id") != run_id:
                    continue
                yield _sse(str(message.get("type") or "message"), message)
        finally:
            await automation_event_broker.unsubscribe(flow_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


