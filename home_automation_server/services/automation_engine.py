"""
Automation engine – executes AutomationFlow actions.
"""

from __future__ import annotations

import json
import logging

from sqlmodel import Session, select

from home_automation_server.models.models import AutomationFlow, AppleTVDevice, AppleTVPairing
from home_automation_server.services import pyatv_service

logger = logging.getLogger(__name__)


def _build_credentials(pairings: list[AppleTVPairing]) -> dict[str, str]:
    return {p.protocol: p.credentials for p in pairings}


async def execute_flow(flow_id: int, session: Session) -> dict:
    """
    Look up an AutomationFlow by ID and execute its action.
    Returns a result dict with status information.
    """
    flow = session.get(AutomationFlow, flow_id)
    if flow is None:
        raise ValueError(f"AutomationFlow {flow_id} not found.")

    device = session.get(AppleTVDevice, flow.device_id)
    if device is None:
        raise ValueError(f"Device {flow.device_id} not found.")

    pairings = session.exec(
        select(AppleTVPairing).where(AppleTVPairing.device_id == device.id)
    ).all()
    credentials = _build_credentials(pairings)

    action_payload: dict = json.loads(flow.action_payload or "{}")
    logger.info(
        "Executing flow '%s' (action=%s) on device '%s'",
        flow.name,
        flow.action_type,
        device.name,
    )

    match flow.action_type:
        case "launch_app":
            bundle_id = action_payload.get("bundle_id")
            if not bundle_id:
                raise ValueError("action_payload must contain 'bundle_id' for launch_app action.")
            await pyatv_service.launch_app(
                device.identifier, device.ip_address, credentials, bundle_id
            )
            return {"status": "ok", "action": "launch_app", "bundle_id": bundle_id}

        case "remote_command":
            command = action_payload.get("command")
            if not command:
                raise ValueError("action_payload must contain 'command' for remote_command action.")
            await pyatv_service.send_remote_command(
                device.identifier, device.ip_address, credentials, command
            )
            return {"status": "ok", "action": "remote_command", "command": command}

        case "power":
            turn_on = action_payload.get("turn_on", True)
            await pyatv_service.power_toggle(
                device.identifier, device.ip_address, credentials, bool(turn_on)
            )
            return {"status": "ok", "action": "power", "turn_on": turn_on}

        case _:
            raise ValueError(f"Unknown action_type: {flow.action_type}")

