"""Tests for /devices/samsung endpoints."""

from fastapi.testclient import TestClient

from home_automation_server.services.samsungtv_service import DiscoveredSamsungDevice


def test_list_samsung_devices_empty(client: TestClient):
    res = client.get("/devices/samsung")
    assert res.status_code == 200
    assert res.json() == []


def test_create_and_get_samsung_device(client: TestClient):
    payload = {
        "name": "Basement Samsung",
        "ip_address": "192.168.1.50",
        "model_year": 2022,
        "port": 8002,
        "token": None,
        "mac_address": "AA:BB:CC:DD:EE:11",
    }

    res = client.post("/devices/samsung", json=payload)
    assert res.status_code == 201
    created = res.json()
    assert created["name"] == payload["name"]
    assert created["ip_address"] == payload["ip_address"]
    assert created["model_year"] == payload["model_year"]

    get_res = client.get(f"/devices/samsung/{created['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["port"] == 8002


def test_delete_samsung_device(client: TestClient):
    res = client.post(
        "/devices/samsung",
        json={
            "name": "Kitchen Samsung",
            "ip_address": "192.168.1.51",
            "model_year": 2024,
            "port": 8002,
            "token": None,
            "mac_address": None,
        },
    )
    assert res.status_code == 201
    device_id = res.json()["id"]

    del_res = client.delete(f"/devices/samsung/{device_id}")
    assert del_res.status_code == 204

    get_res = client.get(f"/devices/samsung/{device_id}")
    assert get_res.status_code == 404


def test_scan_samsung_devices(client: TestClient, monkeypatch):
    async def fake_scan_for_samsung_devices_with_airplay(airplay_devices=None, timeout=4.0):
        return [
            DiscoveredSamsungDevice(
                name="Living Room Samsung",
                ip_address="192.168.1.60",
                model="QN90",
                model_year=2022,
                port=8002,
            )
        ]

    monkeypatch.setattr(
        "home_automation_server.api.devices.samsungtv_service.scan_for_samsung_devices_with_airplay",
        fake_scan_for_samsung_devices_with_airplay,
    )

    res = client.post("/devices/samsung/scan")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["ip_address"] == "192.168.1.60"


def test_pair_samsung_device_saves_token(client: TestClient, monkeypatch):
    create_res = client.post(
        "/devices/samsung",
        json={
            "name": "Pair Samsung",
            "ip_address": "192.168.1.61",
            "model_year": 2023,
            "port": 8002,
            "token": None,
            "mac_address": None,
        },
    )
    assert create_res.status_code == 201
    device_id = create_res.json()["id"]

    async def fake_pair_samsung_device(ip_address: str, port: int = 8002, token: str | None = None):
        assert ip_address == "192.168.1.61"
        assert port == 8002
        return "new-token-123"

    monkeypatch.setattr(
        "home_automation_server.api.devices.samsungtv_service.pair_samsung_device",
        fake_pair_samsung_device,
    )

    pair_res = client.post(f"/devices/samsung/{device_id}/pair", json={"token": None})
    assert pair_res.status_code == 200
    body = pair_res.json()
    assert body["paired"] is True
    assert body["token_saved"] is True
    assert body["has_token"] is True

    get_res = client.get(f"/devices/samsung/{device_id}")
    assert get_res.status_code == 200
    assert get_res.json()["token"] == "new-token-123"


