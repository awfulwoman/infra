"""Tests for the uptime-kuma-api sidecar Flask app.

Run with: pytest test_app.py -v
"""

import os
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("UPTIME_KUMA_URL", "http://uptime-kuma:3001")
os.environ.setdefault("UPTIME_KUMA_USERNAME", "test-user")
os.environ.setdefault("UPTIME_KUMA_PASSWORD", "test-pass")
os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("MONITOR_TAG", "ansible-managed")

from app import create_app  # noqa: E402


@pytest.fixture
def mock_kuma():
    """Mock UptimeKumaApi instance used as the active session."""
    mock = MagicMock()
    mock.get_monitors.return_value = []
    mock.get_tags.return_value = [{"id": 1, "name": "ansible-managed", "color": "#7c8eef"}]
    mock.add_monitor.return_value = {"msg": "Added Successfully.", "monitorID": 99}
    mock.delete_monitor.return_value = {"msg": "Deleted Successfully."}
    mock.add_tag.return_value = {"id": 1, "name": "ansible-managed", "color": "#7c8eef"}
    mock.add_monitor_tag.return_value = {"msg": "Added Successfully."}
    return mock


@pytest.fixture
def client(mock_kuma):
    """Flask test client wired to the mock kuma session."""
    app = create_app(uptime_api_factory=lambda: mock_kuma)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def auth_headers():
    return {"X-API-Key": "test-key"}


# ---- /health ----

def test_health_returns_ok_without_auth(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


# ---- auth ----

def test_endpoints_reject_missing_api_key(client):
    assert client.get("/monitors").status_code == 401
    assert client.post("/monitors", json={}).status_code == 401
    assert client.delete("/monitors/1").status_code == 401
    assert client.post("/monitors/sync", json={"monitors": []}).status_code == 401


def test_endpoints_reject_wrong_api_key(client):
    headers = {"X-API-Key": "nope"}
    assert client.get("/monitors", headers=headers).status_code == 401


# ---- GET /monitors ----

def test_list_monitors_returns_kuma_data(client, mock_kuma):
    mock_kuma.get_monitors.return_value = [
        {"id": 1, "name": "foo", "type": "http", "url": "https://foo", "tags": []},
    ]
    response = client.get("/monitors", headers=auth_headers())
    assert response.status_code == 200
    body = response.get_json()
    assert body == [{"id": 1, "name": "foo", "type": "http", "url": "https://foo", "tags": []}]
    mock_kuma.get_monitors.assert_called_once()


# ---- POST /monitors ----

def test_create_http_monitor(client, mock_kuma):
    payload = {"name": "jellyfin", "type": "http", "url": "https://jellyfin.example"}
    response = client.post("/monitors", headers=auth_headers(), json=payload)
    assert response.status_code == 201
    body = response.get_json()
    assert body["monitorID"] == 99
    mock_kuma.add_monitor.assert_called_once()
    kwargs = mock_kuma.add_monitor.call_args.kwargs
    assert kwargs["name"] == "jellyfin"
    assert kwargs["url"] == "https://jellyfin.example"
    assert "type" in kwargs


def test_create_ping_monitor(client, mock_kuma):
    payload = {"name": "homebrain", "type": "ping", "hostname": "192.168.1.130"}
    response = client.post("/monitors", headers=auth_headers(), json=payload)
    assert response.status_code == 201
    kwargs = mock_kuma.add_monitor.call_args.kwargs
    assert kwargs["name"] == "homebrain"
    assert kwargs["hostname"] == "192.168.1.130"


def test_create_monitor_rejects_unknown_type(client):
    response = client.post(
        "/monitors",
        headers=auth_headers(),
        json={"name": "x", "type": "carrier-pigeon"},
    )
    assert response.status_code == 400
    assert "type" in response.get_json()["error"].lower()


def test_create_monitor_rejects_missing_name(client):
    response = client.post(
        "/monitors",
        headers=auth_headers(),
        json={"type": "ping", "hostname": "1.2.3.4"},
    )
    assert response.status_code == 400


# ---- DELETE /monitors/<id> ----

def test_delete_monitor(client, mock_kuma):
    response = client.delete("/monitors/42", headers=auth_headers())
    assert response.status_code == 200
    mock_kuma.delete_monitor.assert_called_once_with(42)


# ---- POST /monitors/sync ----

def test_sync_creates_missing_monitors(client, mock_kuma):
    mock_kuma.get_monitors.return_value = []
    desired = {
        "monitors": [
            {"name": "homebrain", "type": "ping", "hostname": "192.168.1.130"},
            {"name": "jellyfin.example", "type": "http", "url": "https://jellyfin.example"},
        ]
    }
    response = client.post("/monitors/sync", headers=auth_headers(), json=desired)
    assert response.status_code == 200
    body = response.get_json()
    assert body["created"] == 2
    assert body["deleted"] == 0
    assert body["skipped"] == 0
    assert mock_kuma.add_monitor.call_count == 2
    assert mock_kuma.add_monitor_tag.call_count == 2


def test_sync_skips_existing_managed_monitors(client, mock_kuma):
    mock_kuma.get_monitors.return_value = [
        {
            "id": 7,
            "name": "homebrain",
            "type": "ping",
            "hostname": "192.168.1.130",
            "tags": [{"name": "ansible-managed"}],
        },
    ]
    desired = {
        "monitors": [
            {"name": "homebrain", "type": "ping", "hostname": "192.168.1.130"},
        ]
    }
    response = client.post("/monitors/sync", headers=auth_headers(), json=desired)
    assert response.status_code == 200
    body = response.get_json()
    assert body["created"] == 0
    assert body["deleted"] == 0
    assert body["skipped"] == 1
    mock_kuma.add_monitor.assert_not_called()
    mock_kuma.delete_monitor.assert_not_called()


def test_sync_deletes_managed_monitors_no_longer_desired(client, mock_kuma):
    mock_kuma.get_monitors.return_value = [
        {
            "id": 11,
            "name": "old-thing",
            "type": "http",
            "url": "https://old.example",
            "tags": [{"name": "ansible-managed"}],
        },
    ]
    response = client.post("/monitors/sync", headers=auth_headers(), json={"monitors": []})
    assert response.status_code == 200
    body = response.get_json()
    assert body["created"] == 0
    assert body["deleted"] == 1
    assert body["skipped"] == 0
    mock_kuma.delete_monitor.assert_called_once_with(11)


def test_sync_never_touches_user_managed_monitors(client, mock_kuma):
    mock_kuma.get_monitors.return_value = [
        {
            "id": 21,
            "name": "personal-blog",
            "type": "http",
            "url": "https://blog.example",
            "tags": [],
        },
    ]
    response = client.post("/monitors/sync", headers=auth_headers(), json={"monitors": []})
    assert response.status_code == 200
    body = response.get_json()
    assert body["deleted"] == 0
    mock_kuma.delete_monitor.assert_not_called()


def test_sync_rejects_missing_monitors_key(client):
    response = client.post("/monitors/sync", headers=auth_headers(), json={})
    assert response.status_code == 400
