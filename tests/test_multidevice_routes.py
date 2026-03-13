"""Tests for multi-device control and app launch routes."""
from fastapi.testclient import TestClient
from home_automation_server.services import pyatv_service
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
    res = client.post(
        "/devices/",
        json={
            "name": "Living Room Apple TV",
            "identifier": "AA:BB:CC:22:33:44",
            "ip_address": "192.168.1.12",
        },
    )
    assert res.status_code == 201
    return res.json()["id"]
def test_samsung_controls_and_launch_routes(client: TestClient, monkeypatch):
    device_id = _create_samsung_device(client)
    called: dict[str, str] = {}
    async def fake_send_command(self, command: str):
        called["command"] = command
    async def fake_power(self, turn_on: bool):
        called["power"] = "on" if turn_on else "off"
    async def fake_launch_app(self, app_id: str):
        called["app_id"] = app_id
    monkeypatch.setattr(SamsungTVProvider, "send_command", fake_send_command)
    monkeypatch.setattr(SamsungTVProvider, "power", fake_power)
    monkeypatch.setattr(SamsungTVProvider, "launch_app", fake_launch_app)
    cmd_res = client.post("/controls/samsung/command", json={"device_id": device_id, "command": "home"})
    assert cmd_res.status_code == 200
    assert called["command"] == "home"
    power_res = client.post("/controls/samsung/power", json={"device_id": device_id, "turn_on": False})
    assert power_res.status_code == 200
    assert called["power"] == "off"
    launch_res = client.post("/apps/samsung/launch", json={"device_id": device_id, "app_id": "11101200001"})
    assert launch_res.status_code == 200
    assert called["app_id"] == "11101200001"
    by_kind_res = client.post(
        "/controls/command/by-kind",
        json={"device_kind": "samsung_tv", "device_id": device_id, "command": "back"},
    )
    assert by_kind_res.status_code == 200
    assert called["command"] == "back"
def test_legacy_apple_launch_route_still_works(client: TestClient, monkeypatch):
    device_id = _create_appletv_device(client)
    called: dict[str, str] = {}
    async def fake_launch(identifier: str, ip_address: str, credentials: dict[str, str], bundle_id: str):
        called["identifier"] = identifier
        called["bundle_id"] = bundle_id
    monkeypatch.setattr(pyatv_service, "launch_app", fake_launch)
    res = client.post(
        "/apps/launch",
        json={"device_id": device_id, "bundle_id": "com.netflix.Netflix"},
    )
    assert res.status_code == 200
    assert called["bundle_id"] == "com.netflix.Netflix"
def test_apps_launch_by_kind_path_for_samsung(client: TestClient, monkeypatch):
    device_id = _create_samsung_device(client)
    called: dict[str, str] = {}
    async def fake_launch_app(self, app_id: str):
        called["app_id"] = app_id
    monkeypatch.setattr(SamsungTVProvider, "launch_app", fake_launch_app)
    res = client.post(f"/apps/device/samsung_tv/{device_id}/launch/3201606009684")
    assert res.status_code == 200
    assert called["app_id"] == "3201606009684"
