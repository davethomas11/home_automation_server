"""
Tests for /apps endpoints.
"""

from fastapi.testclient import TestClient


def _create_device(client: TestClient) -> int:
    res = client.post("/devices/", json={
        "name": "App Test TV", "identifier": "app-test-id", "ip_address": "10.0.0.2"
    })
    return res.json()["id"]


def test_create_and_list_app_config(client: TestClient):
    device_id = _create_device(client)
    payload = {
        "device_id": device_id,
        "app_name": "Netflix",
        "bundle_id": "com.netflix.Netflix",
    }
    res = client.post("/apps/configs", json=payload)
    assert res.status_code == 201
    assert res.json()["bundle_id"] == "com.netflix.Netflix"

    list_res = client.get("/apps/configs")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1


def test_delete_app_config(client: TestClient):
    device_id = _create_device(client)
    res = client.post("/apps/configs", json={
        "device_id": device_id, "app_name": "YouTube", "bundle_id": "com.google.ios.youtube"
    })
    config_id = res.json()["id"]

    del_res = client.delete(f"/apps/configs/{config_id}")
    assert del_res.status_code == 204

