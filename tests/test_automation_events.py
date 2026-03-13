"""Tests for automation SSE progress events."""

from fastapi.testclient import TestClient

from home_automation_server.services.provider_resolver import ResolvedProvider


def _create_appletv_device(client: TestClient) -> int:
    res = client.post(
        "/devices/",
        json={"name": "Flow TV", "identifier": "flow-sse-1", "ip_address": "10.0.0.21"},
    )
    assert res.status_code == 201
    return res.json()["id"]


def test_flow_events_stream_emits_engine_progress(client: TestClient, monkeypatch):
    device_id = _create_appletv_device(client)

    class FakeProvider:
        async def send_command(self, command: str):
            return None

        async def power(self, turn_on: bool):
            return None

        async def launch_app(self, app_id: str):
            return None

    def fake_resolve_provider(kind, requested_device_id, session):
        assert requested_device_id == device_id
        return ResolvedProvider(provider=FakeProvider(), device_name="Flow TV")

    monkeypatch.setattr("home_automation_server.services.automation_engine.resolve_provider", fake_resolve_provider)

    flow_res = client.post(
        "/automations/",
        json={
            "device_id": device_id,
            "name": "SSE flow",
            "trigger_type": "manual",
            "trigger_payload": "{}",
            "action_type": "sequence",
            "action_payload": '{"step_delay_ms":0,"actions":[{"type":"remote_command","payload":{"command":"home"}},{"type":"remote_command","payload":{"command":"menu"}}]}',
        },
    )
    assert flow_res.status_code == 201
    flow_id = flow_res.json()["id"]

    run_id = "test-run-sse-1"
    run_res = client.post(f"/automations/{flow_id}/run?run_id={run_id}")
    assert run_res.status_code == 200

    seen_events: list[str] = []
    with client.stream("GET", f"/automations/{flow_id}/events?run_id={run_id}&timeout_seconds=2") as stream:
        for line in stream.iter_lines():
            if not line:
                continue
            text = line.decode() if isinstance(line, bytes) else line
            if text.startswith("event: "):
                seen_events.append(text.replace("event: ", "", 1).strip())
            if "flow_completed" in seen_events:
                break

    assert "connected" in seen_events
    assert "flow_started" in seen_events
    assert "step_started" in seen_events
    assert "step_completed" in seen_events
    assert "flow_completed" in seen_events

