import urllib.parse

import pytest

from op_connect_client import OpConnectClient, OpConnectError

VAULT = "a" * 26
HOST = "https://connect.example.test"


class FakeHttp:
    """Stands in for the HTTP layer: maps URL path (+query) to a JSON reply."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, url, token):
        self.calls.append(url)
        reply = self.routes.get(url.removeprefix(HOST))
        if isinstance(reply, Exception):
            raise reply
        if reply is None:
            raise AssertionError(f"unexpected request: {url}")
        return reply


def items_url(title):
    return f"/v1/vaults/{VAULT}/items?filter=" + urllib.parse.quote(f'title eq "{title}"', safe="")


def make(items, fields_by_id, title="External - Github"):
    routes = {
        items_url(title): [
            {"id": i, "title": title} for i in items
        ]
    }
    for item_id, fields in fields_by_id.items():
        routes[f"/v1/vaults/{VAULT}/items/{item_id}"] = {"id": item_id, "title": title, "fields": fields}
    http = FakeHttp(routes)
    return OpConnectClient(HOST, "tok", VAULT, http=http), http


def test_field_by_label():
    client, _ = make(["i1"], {"i1": [{"id": "x1", "label": "token", "value": "s3cret"}]})
    assert client.get_field("External - Github", "token") == "s3cret"


def test_field_by_id_when_no_label_matches():
    client, _ = make(["i1"], {"i1": [{"id": "password", "purpose": "PASSWORD", "value": "pw"}]})
    assert client.get_field("External - Github", "password") == "pw"


def test_label_wins_over_id():
    fields = [
        {"id": "password", "value": "by-id"},
        {"id": "z", "label": "password", "value": "by-label"},
    ]
    client, _ = make(["i1"], {"i1": fields})
    assert client.get_field("External - Github", "password") == "by-label"


def test_item_missing():
    client, _ = make([], {})
    with pytest.raises(OpConnectError, match="External - Github"):
        client.get_field("External - Github", "token")


def test_field_missing_names_title_and_field():
    client, _ = make(["i1"], {"i1": [{"id": "a", "label": "other", "value": "v"}]})
    with pytest.raises(OpConnectError, match="External - Github.*token"):
        client.get_field("External - Github", "token")


def test_duplicate_titles():
    client, _ = make(["i1", "i2"], {})
    with pytest.raises(OpConnectError, match="2 items"):
        client.get_field("External - Github", "token")


def test_duplicate_labels_in_one_item():
    fields = [{"id": "a", "label": "token", "value": "1"}, {"id": "b", "label": "token", "value": "2"}]
    client, _ = make(["i1"], {"i1": fields})
    with pytest.raises(OpConnectError, match="duplicate"):
        client.get_field("External - Github", "token")


def test_unlabelled_fields_are_skipped():
    fields = [{"id": "n1", "value": "ignored"}, {"id": "a", "label": "token", "value": "ok"}]
    client, _ = make(["i1"], {"i1": fields})
    assert client.get_field("External - Github", "token") == "ok"


def test_title_with_spaces_and_dash():
    title = "Login - Grafana (charlie)"
    client, _ = make(["i1"], {"i1": [{"id": "username", "value": "charlie"}]}, title=title)
    assert client.get_field(title, "username") == "charlie"


def test_http_error_names_title_not_value():
    routes = {f"/v1/vaults/{VAULT}/items?filter=title%20eq%20%22T%22": OpConnectError("HTTP 503")}
    client = OpConnectClient(HOST, "tok", VAULT, http=FakeHttp(routes))
    with pytest.raises(OpConnectError, match="503"):
        client.get_field("T", "f")


def test_item_is_cached_per_client():
    client, http = make(["i1"], {"i1": [{"id": "a", "label": "x", "value": "1"}, {"id": "b", "label": "y", "value": "2"}]})
    client.get_field("External - Github", "x")
    client.get_field("External - Github", "y")
    assert len(http.calls) == 2  # one search, one item fetch


def test_empty_value_raises():
    client, _ = make(["i1"], {"i1": [{"id": "a", "label": "x", "value": ""}]})
    with pytest.raises(OpConnectError, match="empty"):
        client.get_field("External - Github", "x")


def test_vault_title_resolved_to_id():
    routes = {
        "/v1/vaults?filter=name%20eq%20%22Infra%22": [{"id": VAULT, "name": "Infra"}],
        f"/v1/vaults/{VAULT}/items?filter=title%20eq%20%22T%22": [{"id": "i1"}],
        f"/v1/vaults/{VAULT}/items/i1": {"fields": [{"id": "a", "label": "f", "value": "v"}]},
    }
    client = OpConnectClient(HOST, "tok", "Infra", http=FakeHttp(routes))
    assert client.get_field("T", "f") == "v"
