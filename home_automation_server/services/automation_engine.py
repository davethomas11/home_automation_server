"""
Automation engine – executes AutomationFlow actions.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from sqlmodel import Session, select

from home_automation_server.models.models import AutomationFlow, AppleTVDevice, AppleTVPairing
from home_automation_server.services import pyatv_service

logger = logging.getLogger(__name__)



def _build_credentials(pairings: list[AppleTVPairing]) -> dict[str, str]:
    return {p.protocol: p.credentials for p in pairings}


async def _execute_single_action(
    *,
    device: AppleTVDevice,
    credentials: dict[str, str],
    action_type: str,
    action_payload: dict[str, Any],
) -> dict[str, Any]:
    """Execute one action and return a result payload."""
    match action_type:
        case "wait_seconds":
            seconds = action_payload.get("seconds", 1)
            try:
                delay = float(seconds)
            except (TypeError, ValueError) as exc:
                raise ValueError("action_payload.seconds must be a number for wait_seconds action.") from exc

            if delay < 0:
                raise ValueError("action_payload.seconds must be >= 0 for wait_seconds action.")

            await asyncio.sleep(delay)
            return {"status": "ok", "action": "wait_seconds", "seconds": delay}

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

        case "swipe":
            direction = action_payload.get("direction")
            start_x = action_payload.get("start_x")
            start_y = action_payload.get("start_y")
            end_x = action_payload.get("end_x")
            end_y = action_payload.get("end_y")
            duration_ms = action_payload.get("duration_ms", 300)

            if not direction and None in (start_x, start_y, end_x, end_y):
                raise ValueError(
                    "action_payload must contain either 'direction' or all of "
                    "'start_x', 'start_y', 'end_x', 'end_y' for swipe action."
                )

            await pyatv_service.swipe_gesture(
                device.identifier,
                device.ip_address,
                credentials,
                direction=direction,
                start_x=start_x,
                start_y=start_y,
                end_x=end_x,
                end_y=end_y,
                duration_ms=int(duration_ms),
            )
            result: dict[str, Any] = {"status": "ok", "action": "swipe", "duration_ms": duration_ms}
            if direction:
                result["direction"] = direction
            else:
                result.update({"start_x": start_x, "start_y": start_y, "end_x": end_x, "end_y": end_y})
            return result

        case _:
            raise ValueError(f"Unknown action_type: {action_type}")


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

    action_payload: dict[str, Any] = json.loads(flow.action_payload or "{}")
    logger.info(
        "Executing flow '%s' (action=%s) on device '%s'",
        flow.name,
        flow.action_type,
        device.name,
    )

    if flow.action_type == "sequence":
        # Expected payload shape:
        # {
        #   "actions": [
        #     {"type": "power", "payload": {"turn_on": true}},
        #     {"type": "launch_app", "payload": {"bundle_id": "com.netflix.Netflix"}}
        #   ]
        # }
        actions = action_payload.get("actions")
        if not isinstance(actions, list) or not actions:
            raise ValueError("action_payload must contain a non-empty 'actions' list for sequence action.")

        results: list[dict[str, Any]] = []
        for index, item in enumerate(actions, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"actions[{index}] must be an object.")

            sub_type = item.get("type") or item.get("action_type")
            sub_payload = item.get("payload")
            if sub_payload is None:
                sub_payload = item.get("action_payload", {})

            if not isinstance(sub_type, str) or not sub_type:
                raise ValueError(f"actions[{index}] must include 'type' (or 'action_type').")
            if not isinstance(sub_payload, dict):
                raise ValueError(f"actions[{index}] payload must be an object.")

            result = await _execute_single_action(
                device=device,
                credentials=credentials,
                action_type=sub_type,
                action_payload=sub_payload,
            )
            results.append({"step": index, **result})

        return {
            "status": "ok",
            "action": "sequence",
            "steps": len(results),
            "results": results,
        }

    return await _execute_single_action(
        device=device,
        credentials=credentials,
        action_type=flow.action_type,
        action_payload=action_payload,
    )

