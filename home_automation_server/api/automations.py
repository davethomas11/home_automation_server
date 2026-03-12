"""
/automations router – manage and execute automation flows.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from home_automation_server.db.session import get_session
from home_automation_server.models.models import (
    AutomationFlow,
    AutomationFlowCreate,
    AutomationFlowRead,
)
from home_automation_server.services.automation_engine import execute_flow

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/", response_model=list[AutomationFlowRead], summary="List all automation flows")
def list_flows(session: SessionDep):
    return session.exec(select(AutomationFlow)).all()


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


@router.delete("/{flow_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a flow")
def delete_flow(flow_id: int, session: SessionDep):
    flow = session.get(AutomationFlow, flow_id)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")
    session.delete(flow)
    session.commit()


@router.post("/{flow_id}/run", summary="Manually trigger a flow")
async def run_flow(flow_id: int, session: SessionDep):
    """Execute a flow immediately (manual trigger)."""
    try:
        result = await execute_flow(flow_id, session)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    return result

