import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("ohp", Path(__file__).parent.parent / "scripts" / "op-host-password.py")
ohp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ohp)


class FakeClient:
    def __init__(self, items):
        self.items, self.calls = items, []

    def call(self, method, path="", body=None, query=""):
        self.calls.append((method, path))
        if method == "GET" and not path:
            return [i for i in self.items]
        if method == "GET":
            return self.items[0]
        return body if method == "POST" and not self.items else {"id": "new"}


def test_set_password_replaces_value_and_ensures_tags():
    item = {"fields": [{"id": "password", "label": "password", "value": "old"}], "tags": ["host"]}
    out = ohp.set_password(item, "new")
    assert out["fields"][0]["value"] == "new"
    assert out["tags"] == ["ansible", "host"]


def test_set_password_adds_missing_field():
    out = ohp.set_password({"fields": [{"id": "username", "value": "x"}]}, "new")
    assert out["fields"][-1]["id"] == "password"


def test_build_item_is_server_with_tags():
    item = ohp.build_item("Host - X", "v")
    assert item["category"] == "SERVER" and item["tags"] == ["host", "ansible"]


def test_store_creates_when_missing():
    client = FakeClient([])
    client.call = lambda m, p="", body=None, query="": [] if m == "GET" else {"id": "n1"}
    assert ohp.store(client, "Host - X", "v") == ("created", "n1")
