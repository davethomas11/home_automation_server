"""Tests for the multi-device controls UI page."""

from fastapi.testclient import TestClient


def test_controls_page_without_devices_shows_empty_state(client: TestClient):
    res = client.get("/ui/controls", follow_redirects=False)
    assert res.status_code == 200
    assert "No devices saved." in res.text


def test_controls_page_redirects_to_first_device_route(client: TestClient):
    apple_res = client.post(
        "/devices/",
        json={
            "name": "Living Room Apple TV",
            "identifier": "apple-ui-1",
            "ip_address": "192.168.1.10",
        },
    )
    assert apple_res.status_code == 201

    res = client.get("/ui/controls", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["location"] == f"/ui/controls/apple_tv/{apple_res.json()['id']}"


def test_controls_page_renders_selected_device_controls_and_subnav(client: TestClient):
    apple_res = client.post(
        "/devices/",
        json={
            "name": "Living Room Apple TV",
            "identifier": "apple-ui-2",
            "ip_address": "192.168.1.10",
        },
    )
    assert apple_res.status_code == 201

    samsung_res = client.post(
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
    assert samsung_res.status_code == 201

    apple_id = apple_res.json()["id"]
    samsung_id = samsung_res.json()["id"]

    res = client.get(f"/ui/controls/apple_tv/{apple_id}")
    assert res.status_code == 200

    html = res.text
    assert "Apple TV Remote" in html
    assert "Samsung TV Remote" not in html
    assert "atvCmd('home')" in html
    assert "samsungCmd('home')" not in html
    assert f'/ui/controls/apple_tv/{apple_id}' in html
    assert f'/ui/controls/samsung_tv/{samsung_id}' in html
    assert 'header-subnav' in html
    assert 'header-subnav-link is-active' in html
    assert 'Living Room Apple TV (Apple TV)' in html
    assert 'Basement Samsung' in html
    assert 'Choose a saved device to open its dedicated controls page.' not in html
    assert 'remote-shell-apple' in html
    assert 'Record automation' in html
    assert 'Start Recording' in html
    assert 'recording-pulse-overlay' in html
    assert 'automation-recorder-launcher' in html
    assert 'Live Log' in html


def test_controls_page_renders_samsung_specific_controls(client: TestClient):
    samsung_res = client.post(
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
    assert samsung_res.status_code == 201

    samsung_id = samsung_res.json()["id"]
    res = client.get(f"/ui/controls/samsung_tv/{samsung_id}")
    assert res.status_code == 200

    html = res.text
    assert "Samsung TV Remote" in html
    assert "Apple TV Remote" not in html
    assert "samsungCmd('home')" in html
    assert "atvCmd('home')" not in html
    assert 'remote-shell-samsung' in html
    assert 'Record automation' in html
    assert 'Save as Flow' in html
    assert 'recording-pulse-overlay' in html
    assert 'automation-recorder-launcher' in html
    assert 'Live Log' in html

    # New buttons
    assert "samsungCmd('up')" in html
    assert "samsungCmd('select')" in html
    assert "samsungCmd('source')" in html
    assert "samsungCmd('settings')" in html
    assert "samsungCmd('info')" in html
    assert "samsungCmd('num_1')" in html
    assert "samsungCmd('num_0')" in html
    assert "samsungCmd('red')" in html
    assert "samsungCmd('channel_up')" in html
    assert "samsungCmd('fast_forward')" in html





