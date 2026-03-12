"""
Tests for /devices endpoints.
"""

from fastapi.testclient import TestClient


def test_list_devices_empty(client: TestClient):
    res = client.get("/devices/")
    assert res.status_code == 200
    assert res.json() == []


def test_create_and_get_device(client: TestClient):
    payload = {
        "name": "Living Room",
        "identifier": "AA:BB:CC:DD:EE:FF",
        "ip_address": "192.168.1.10",
    }
    res = client.post("/devices/", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Living Room"
    assert data["identifier"] == "AA:BB:CC:DD:EE:FF"
    device_id = data["id"]

    res2 = client.get(f"/devices/{device_id}")
    assert res2.status_code == 200
    assert res2.json()["ip_address"] == "192.168.1.10"


def test_delete_device(client: TestClient):
    payload = {
        "name": "Bedroom",
        "identifier": "11:22:33:44:55:66",
        "ip_address": "192.168.1.11",
    }
    res = client.post("/devices/", json=payload)
    device_id = res.json()["id"]

    del_res = client.delete(f"/devices/{device_id}")
    assert del_res.status_code == 204

    get_res = client.get(f"/devices/{device_id}")
    assert get_res.status_code == 404


def test_get_nonexistent_device(client: TestClient):
    res = client.get("/devices/9999")
    assert res.status_code == 404

