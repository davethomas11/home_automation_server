"""Tests for multi-device automation execution."""
from fastapi.testclient import TestClient
from home_automation_server.services.provider_resolver import ResolvedProvider
from home_automation_server.services.samsungtv_service import SamsungTVProvider
def _create_samsung_device(client: TestClient) -> int:
    res = client.post(
        "/devices/samsung",
        json={
            "name": "Basement Samsung",
            "ip_address": "192.168.1.50",
            "model_year": 2022,
            "port": 8002,
            "token": None,
            "mac_address": None,
        },
    )
    assert res.status_code == 201
    return res.json()["id"]
def _create_appletv_device(client: TestClient) -> int:
    device_res = client.post(
        "/devices/",
        json={"name": "Apple TV", "identifier": "id-flow-1", "ip_address": "10.0.0.3"},
    )
    assert device_res.status_code == 201
    return device_res.json()["id"]
def test_run_samsung_flow_sequence(client: TestClient, monkeypatch):
    device_id = _create_samsung_device(client)
    called: list[str] = []
    async def fake_send_command(self, command: str):
        called.append(f"cmd:{command}")
    async def fake_launch_app(self, app_id: str):
        called.append(f"app:{app_id}")
    monkeypatch.setattr(SamsungTVProvider, "send_command", fake_send_command)
    monkeypatch.setattr(SamsungTVProvider, "launch_app", fake_launch_app)
    flow_res = client.post(
        "/automations/",
        json={
            "device_kind": "samsung_tv",
            "device_id": device_id,
            "name": "Samsung startup",
            "trigger_type": "manual",
            "trigger_payload": "{}",
            "action_type": "sequence",
            "action_payload": '{"actions":[{"type":"remote_command","payload":{"command":"home"}},{"type":"launch_app","payload":{"app_id":"11101200001"}}]}',
        },
    )
    assert flow_res.status_code == 201
    flow_id = flow_res.json()["id"]
    run_res = client.post(f"/automations/{flow_id}/run")
    assert run_res.status_code == 200
    assert called == ["cmd:home", "app:11101200001"]
def test_run_apple_flow_backward_compatible(client: TestClient, monkeypatch):
    device_id = _create_appletv_device(client)
    called: dict[str, str] = {}
    class FakeAppleProvider:
        async def send_command(self, command: str):
            called["command"] = command
        async def power(self, turn_on: bool):
            called["power"] = str(turn_on)
        async def launch_app(self, app_id: str):
            called["app_id"] = app_id
    def fake_resolve_provider(kind, requested_device_id, session):
        assert requested_device_id == device_id
        return ResolvedProvider(provider=FakeAppleProvider(), device_name="Apple TV")
    monkeypatch.setattr("home_automation_server.services.automation_engine.resolve_provider", fake_resolve_provider)
    flow_res = client.post(
        "/automations/",
        json={
            "device_id": device_id,
            "name": "Legacy Apple flow",
            "trigger_type": "manual",
            "trigger_payload": "{}",
            "action_type": "remote_command",
            "action_payload": '{"command":"menu"}',
        },
    )
    assert flow_res.status_code == 201
    flow_id = flow_res.json()["id"]
    run_res = client.post(f"/automations/{flow_id}/run")
    assert run_res.status_code == 200
    assert called["command"] == "menu"
