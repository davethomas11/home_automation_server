"""
Tests for /automations endpoints.
"""

from fastapi.testclient import TestClient


def _create_device(client: TestClient) -> int:
    res = client.post("/devices/", json={
        "name": "Test TV", "identifier": "test-id-001", "ip_address": "10.0.0.1"
    })
    return res.json()["id"]


def _create_samsung_device(client: TestClient) -> int:
    res = client.post("/devices/samsung", json={
        "name": "Samsung Test TV", "ip_address": "10.0.0.50", "model_year": 2022, "port": 8002,
        "token": None, "mac_address": None,
    })
    return res.json()["id"]


def test_create_and_list_flow(client: TestClient):
    device_id = _create_device(client)
    payload = {
        "device_id": device_id,
        "name": "Open Netflix",
        "trigger_type": "webhook",
        "trigger_payload": "{}",
        "action_type": "launch_app",
        "action_payload": '{"bundle_id":"com.netflix.Netflix"}',
    }
    res = client.post("/automations/", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Open Netflix"
    assert data["action_type"] == "launch_app"

    list_res = client.get("/automations/")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1


def test_update_flow(client: TestClient):
    device_id = _create_device(client)
    res = client.post("/automations/", json={
        "device_id": device_id,
        "name": "Old Name",
        "trigger_type": "manual",
        "trigger_payload": "{}",
        "action_type": "power",
        "action_payload": '{"turn_on":true}',
    })
    flow_id = res.json()["id"]

    update_res = client.put(f"/automations/{flow_id}", json={
        "device_id": device_id,
        "name": "New Name",
        "trigger_type": "manual",
        "trigger_payload": "{}",
        "action_type": "power",
        "action_payload": '{"turn_on":false}',
    })
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "New Name"


def test_delete_flow(client: TestClient):
    device_id = _create_device(client)
    res = client.post("/automations/", json={
        "device_id": device_id,
        "name": "Temp Flow",
        "trigger_type": "manual",
        "trigger_payload": "{}",
        "action_type": "power",
        "action_payload": "{}",
    })
    flow_id = res.json()["id"]

    del_res = client.delete(f"/automations/{flow_id}")
    assert del_res.status_code == 204

    get_res = client.get(f"/automations/{flow_id}")
    assert get_res.status_code == 404


def test_create_and_list_samsung_flow_parity_routes(client: TestClient):
    device_id = _create_samsung_device(client)
    payload = {
        "device_id": device_id,
        "name": "Samsung Home",
        "trigger_type": "manual",
        "trigger_payload": "{}",
        "action_type": "remote_command",
        "action_payload": '{"command":"home"}',
    }

    res = client.post("/automations/samsung", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["device_kind"] == "samsung_tv"

    list_res = client.get("/automations/samsung")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1


def test_create_and_list_appletv_flow_parity_routes(client: TestClient):
    device_id = _create_device(client)
    payload = {
        "device_id": device_id,
        "name": "Apple Menu",
        "trigger_type": "manual",
        "trigger_payload": "{}",
        "action_type": "remote_command",
        "action_payload": '{"command":"menu"}',
    }

    res = client.post("/automations/appletv", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["device_kind"] == "apple_tv"

    list_res = client.get("/automations/appletv")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1


