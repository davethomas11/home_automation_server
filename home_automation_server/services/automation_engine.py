"""
Automation engine – executes AutomationFlow actions.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from sqlmodel import Session, select

from home_automation_server.models.models import AutomationFlow, AppleTVDevice, AppleTVPairing, DeviceKind
from home_automation_server.services.automation_events import broker as automation_event_broker, make_event
from home_automation_server.services import pyatv_service
from home_automation_server.services.provider_resolver import ProviderResolutionError, resolve_provider

logger = logging.getLogger(__name__)



def _build_credentials(pairings: list[AppleTVPairing]) -> dict[str, str]:
    return {p.protocol: p.credentials for p in pairings}


async def _execute_single_action(
    *,
    device_kind: DeviceKind,
    provider,
    apple_device: AppleTVDevice | None,
    apple_credentials: dict[str, str] | None,
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
            app_id = action_payload.get("app_id") or action_payload.get("bundle_id")
            if not app_id:
                raise ValueError("action_payload must contain 'app_id' or 'bundle_id' for launch_app action.")
            await provider.launch_app(str(app_id))
            return {"status": "ok", "action": "launch_app", "app_id": app_id}

        case "remote_command":
            command = action_payload.get("command")
            if not command:
                raise ValueError("action_payload must contain 'command' for remote_command action.")
            await provider.send_command(command)
            return {"status": "ok", "action": "remote_command", "command": command}

        case "power":
            turn_on = action_payload.get("turn_on", True)
            await provider.power(bool(turn_on))
            return {"status": "ok", "action": "power", "turn_on": turn_on}

        case "swipe":
            if device_kind != DeviceKind.APPLE_TV or apple_device is None or apple_credentials is None:
                raise ValueError("Swipe action is currently supported only for apple_tv devices.")

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
                apple_device.identifier,
                apple_device.ip_address,
                apple_credentials,
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


async def execute_flow(flow_id: int, session: Session, run_id: str | None = None) -> dict:
    """
    Look up an AutomationFlow by ID and execute its action.
    Returns a result dict with status information.
    """
    flow = session.get(AutomationFlow, flow_id)
    if flow is None:
        raise ValueError(f"AutomationFlow {flow_id} not found.")

    run_id = run_id or uuid.uuid4().hex

    async def emit(event_type: str, **data: Any) -> None:
        await automation_event_broker.publish(
            flow_id,
            make_event(event_type, flow_id=flow_id, run_id=run_id, **data),
        )

    device_kind = DeviceKind(flow.device_kind)
    try:
        resolved = resolve_provider(device_kind, flow.device_id, session)
    except ProviderResolutionError as exc:
        raise ValueError(str(exc)) from exc

    apple_device: AppleTVDevice | None = None
    apple_credentials: dict[str, str] | None = None
    if device_kind == DeviceKind.APPLE_TV:
        device = session.get(AppleTVDevice, flow.device_id)
        if device is None:
            raise ValueError(f"Device {flow.device_id} not found.")
        pairings = session.exec(
            select(AppleTVPairing).where(AppleTVPairing.device_id == device.id)
        ).all()
        apple_device = device
        apple_credentials = _build_credentials(pairings)

    action_payload: dict[str, Any] = json.loads(flow.action_payload or "{}")
    logger.info(
        "Executing flow '%s' (action=%s) on device '%s'",
        flow.name,
        flow.action_type,
        resolved.device_name,
    )

    if flow.action_type == "sequence":
        # Expected payload shape:
        # {
        #   "step_delay_ms": 200,          ← optional default delay between steps (ms)
        #   "actions": [
        #     {"type": "power", "payload": {"turn_on": true}},
        #     {"type": "launch_app", "payload": {"bundle_id": "com.netflix.Netflix"}}
        #   ]
        # }
        actions = action_payload.get("actions")
        if not isinstance(actions, list) or not actions:
            raise ValueError("action_payload must contain a non-empty 'actions' list for sequence action.")

        # Default inter-step delay in seconds (0 = no delay)
        step_delay_ms = action_payload.get("step_delay_ms", 0)
        try:
            step_delay_s = max(0.0, float(step_delay_ms) / 1000.0)
        except (TypeError, ValueError):
            step_delay_s = 0.0

        await emit(
            "flow_started",
            flow_name=flow.name,
            action_type="sequence",
            total_steps=len(actions),
            step_delay_ms=int(step_delay_ms),
        )

        results: list[dict[str, Any]] = []
        try:
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

                await emit("step_started", step=index, step_index=index - 1, action_type=sub_type)

                result = await _execute_single_action(
                    device_kind=device_kind,
                    provider=resolved.provider,
                    apple_device=apple_device,
                    apple_credentials=apple_credentials,
                    action_type=sub_type,
                    action_payload=sub_payload,
                )
                results.append({"step": index, **result})
                await emit("step_completed", step=index, step_index=index - 1, action_type=sub_type, result=result)

                # Apply inter-step delay after every step except the last
                if step_delay_s > 0 and index < len(actions):
                    await emit("delay_started", step=index, step_index=index - 1, delay_ms=int(step_delay_ms))
                    await asyncio.sleep(step_delay_s)
                    await emit("delay_completed", step=index, step_index=index - 1, delay_ms=int(step_delay_ms))

        except Exception as exc:
            await emit("flow_failed", error=str(exc))
            raise

        result_payload = {
            "status": "ok",
            "action": "sequence",
            "steps": len(results),
            "step_delay_ms": int(step_delay_ms),
            "results": results,
        }
        await emit("flow_completed", result=result_payload)
        return {**result_payload, "run_id": run_id}

    await emit("flow_started", flow_name=flow.name, action_type=flow.action_type, total_steps=1, step_delay_ms=0)
    try:
        await emit("step_started", step=1, step_index=0, action_type=flow.action_type)
        single = await _execute_single_action(
            device_kind=device_kind,
            provider=resolved.provider,
            apple_device=apple_device,
            apple_credentials=apple_credentials,
            action_type=flow.action_type,
            action_payload=action_payload,
        )
        await emit("step_completed", step=1, step_index=0, action_type=flow.action_type, result=single)
    except Exception as exc:
        await emit("flow_failed", error=str(exc))
        raise

    await emit("flow_completed", result=single)
    return {**single, "run_id": run_id}

