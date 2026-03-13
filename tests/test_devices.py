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


def test_appletv_parity_routes(client: TestClient):
    payload = {
        "name": "Office Apple TV",
        "identifier": "AA:BB:CC:11:22:33",
        "ip_address": "192.168.1.42",
    }

    create_res = client.post("/devices/appletv", json=payload)
    assert create_res.status_code == 201
    created = create_res.json()
    device_id = created["id"]

    # New parity routes
    get_new_res = client.get(f"/devices/appletv/{device_id}")
    assert get_new_res.status_code == 200
    assert get_new_res.json()["identifier"] == payload["identifier"]

    list_new_res = client.get("/devices/appletv")
    assert list_new_res.status_code == 200
    assert len(list_new_res.json()) == 1

    # Backward compatibility routes still work with the same record
    get_legacy_res = client.get(f"/devices/{device_id}")
    assert get_legacy_res.status_code == 200
    assert get_legacy_res.json()["name"] == payload["name"]

    delete_new_res = client.delete(f"/devices/appletv/{device_id}")
    assert delete_new_res.status_code == 204

    get_after_delete = client.get(f"/devices/{device_id}")
    assert get_after_delete.status_code == 404


