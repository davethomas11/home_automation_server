"""
/webhooks router – trigger automation flows via HTTP POST.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session, select

from home_automation_server.db.session import get_session
from home_automation_server.models.models import AutomationFlow
from home_automation_server.services.automation_engine import execute_flow

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/trigger/{flow_id}", summary="Trigger an automation flow via webhook")
async def webhook_trigger(flow_id: int, request: Request, session: SessionDep):
    """
    Trigger an AutomationFlow by ID.
    Optionally accepts a JSON body for future payload inspection.
    Validates that the flow has trigger_type == 'webhook'.
    """
    flow = session.get(AutomationFlow, flow_id)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flow not found")

    if flow.trigger_type not in ("webhook", "manual"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Flow trigger_type is '{flow.trigger_type}', not 'webhook'.",
        )

    try:
        result = await execute_flow(flow_id, session)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return {"status": "triggered", "flow_id": flow_id, "result": result}


@router.get("/", summary="List webhook-enabled flows")
def list_webhook_flows(session: SessionDep):
    """Return all flows with trigger_type == 'webhook'."""
    flows = session.exec(
        select(AutomationFlow).where(AutomationFlow.trigger_type == "webhook")
    ).all()
    return flows

