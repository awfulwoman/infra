"""scripts/onepassword.py: plan and apply an item spec against Connect.

The client is faked in memory. Generation is simulated the way Connect does it:
a field sent with generate=true comes back with a value the caller never saw.
"""

import json

import pytest

import onepassword as op

GENERATED = "SERVER-MADE-VALUE"
SECRET = "copied-secret-value"


def spec(**over):
    base = {
        "title": "External - Test",
        "category": "secure_note",
        "tags": ["external", "ansible"],
        "fields": [{"label": "token", "type": "concealed", "generate": "on_create"}],
    }
    base.update(over)
    return base


def existing(fields=None, tags=None, category="SECURE_NOTE", sections=None):
    return {
        "id": "item1",
        "title": "External - Test",
        "category": category,
        "tags": tags if tags is not None else ["external", "ansible"],
        "sections": sections or [],
        "fields": fields if fields is not None else [],
    }


class FakeClient:
    def __init__(self, items=None):
        self.items = {i["title"]: i for i in (items or [])}
        self.writes = []

    def find_item(self, title):
        return self.items.get(title)

    def create_item(self, body):
        self.writes.append(("create", body["title"]))
        item = json.loads(json.dumps(body))
        item["id"] = "new1"
        for f in item["fields"]:
            if f.pop("generate", False):
                f.pop("recipe", None)
                f["value"] = GENERATED
        self.items[item["title"]] = item
        return item

    def replace_item(self, body):
        self.writes.append(("replace", body["title"]))
        item = json.loads(json.dumps(body))
        for f in item["fields"]:
            if f.pop("generate", False):
                f.pop("recipe", None)
                f["value"] = GENERATED
        self.items[item["title"]] = item
        return item


# --- plan: create ----------------------------------------------------------


def test_create_marks_generated_field_and_sends_no_value():
    action, body, changes = op.build_plan(None, spec())
    assert action == "created"
    assert body["category"] == "SECURE_NOTE"
    assert body["tags"] == ["external", "ansible"]
    field = body["fields"][0]
    assert field["generate"] is True and field["type"] == "CONCEALED" and field["label"] == "token"
    assert "value" not in field or field["value"] is None
    assert changes == [{"label": "token", "change": "generated"}]


def test_create_with_value_sends_the_value():
    s = spec(fields=[{"label": "token", "type": "concealed", "value": SECRET}])
    _, body, changes = op.build_plan(None, s)
    assert body["fields"][0]["value"] == SECRET
    assert changes == [{"label": "token", "change": "added"}]


def test_recipe_maps_to_character_sets():
    f = {"label": "token", "type": "concealed", "generate": "on_create",
         "recipe": {"length": 20, "symbols": False}}
    _, body, _ = op.build_plan(None, spec(fields=[f]))
    assert body["fields"][0]["recipe"] == {"length": 20, "characterSets": ["LETTERS", "DIGITS"]}


def test_urls_are_sent_as_primary_first():
    _, body, _ = op.build_plan(None, spec(category="login", urls=["https://x.example"]))
    assert body["urls"] == [{"href": "https://x.example", "primary": True}]


def test_login_builtin_fields_are_marked_by_purpose_not_id():
    s = spec(category="login", fields=[
        {"label": "username", "type": "string", "value": "admin"},
        {"label": "password", "type": "concealed", "generate": "on_create"},
        {"label": "note", "value": "x"},
    ])
    _, body, _ = op.build_plan(None, s)
    username, password, note = body["fields"]
    assert username["purpose"] == "USERNAME" and password["purpose"] == "PASSWORD"
    assert "id" not in username and "id" not in password
    assert "purpose" not in note


def test_password_category_marks_its_password_by_purpose():
    s = spec(category="password", fields=[{"label": "password", "type": "concealed", "generate": "on_create"}])
    _, body, _ = op.build_plan(None, s)
    assert body["fields"][0]["purpose"] == "PASSWORD"


def test_server_builtin_fields_use_id_and_never_purpose():
    s = spec(category="server", fields=[{"label": "password", "type": "concealed", "generate": "on_create"}])
    _, body, _ = op.build_plan(None, s)
    assert body["fields"][0]["id"] == "password" and "purpose" not in body["fields"][0]


def test_second_run_on_a_login_is_ok():
    client = FakeClient()
    s = spec(category="login", fields=[
        {"label": "username", "value": "admin"},
        {"label": "password", "type": "concealed", "generate": "on_create"},
    ])
    op.apply_spec(client, {"items": [s]})
    # Connect names the built-ins by id and purpose; matching is by label.
    for f in client.items["External - Test"]["fields"]:
        f.setdefault("id", f["label"])
    assert op.apply_spec(client, {"items": [s]})["changed"] is False


# --- plan: idempotency and update -----------------------------------------


def test_generate_on_create_leaves_existing_field_alone():
    item = existing([{"id": "f1", "label": "token", "type": "CONCEALED", "value": "old"}])
    action, body, changes = op.build_plan(item, spec())
    assert (action, body, changes) == ("ok", None, [])


def test_generate_on_create_adds_a_missing_field():
    action, body, changes = op.build_plan(existing([]), spec())
    assert action == "updated"
    assert changes == [{"label": "token", "change": "generated"}]
    assert body["fields"][0]["generate"] is True


def test_generate_always_regenerates_every_time():
    f = {"label": "token", "type": "concealed", "generate": "always"}
    item = existing([{"id": "f1", "label": "token", "type": "CONCEALED", "value": "old"}])
    action, body, changes = op.build_plan(item, spec(fields=[f]))
    assert action == "updated"
    assert changes == [{"label": "token", "change": "regenerated"}]
    assert body["fields"][0]["generate"] is True and body["fields"][0]["id"] == "f1"


def test_same_value_is_ok_and_different_value_updates():
    item = existing([{"id": "f1", "label": "token", "type": "CONCEALED", "value": SECRET}])
    s = spec(fields=[{"label": "token", "type": "concealed", "value": SECRET}])
    assert op.build_plan(item, s)[0] == "ok"
    s2 = spec(fields=[{"label": "token", "type": "concealed", "value": "new"}])
    action, body, changes = op.build_plan(item, s2)
    assert action == "updated" and changes == [{"label": "token", "change": "updated"}]
    assert body["fields"][0]["value"] == "new"


def test_label_match_ignores_case():
    item = existing([{"id": "f1", "label": "Token", "type": "CONCEALED", "value": "old"}])
    assert op.build_plan(item, spec())[0] == "ok"


def test_unlisted_fields_and_notes_are_preserved():
    item = existing([
        {"id": "notesPlain", "label": "notesPlain", "type": "STRING", "purpose": "NOTES", "value": "keep me"},
        {"id": "f9", "label": "extra", "type": "STRING", "value": "also keep"},
    ])
    _, body, _ = op.build_plan(item, spec())
    labels = [f["label"] for f in body["fields"]]
    assert "notesPlain" in labels and "extra" in labels and "token" in labels


def test_tags_are_unioned_never_removed():
    item = existing([{"id": "f1", "label": "token", "type": "CONCEALED", "value": "v"}], tags=["host"])
    action, body, changes = op.build_plan(item, spec())
    assert action == "updated"
    assert set(body["tags"]) == {"host", "external", "ansible"}
    assert {"label": "(tags)", "change": "updated"} in changes


def test_category_mismatch_is_an_error():
    with pytest.raises(op.SpecError, match="category"):
        op.build_plan(existing(category="LOGIN"), spec())


def test_sections_group_fields_and_match_by_section():
    s = spec(fields=[{"label": "key", "type": "concealed", "value": "v1", "section": "ZFS"}])
    _, body, _ = op.build_plan(None, s)
    sec = body["sections"][0]
    assert sec["label"] == "ZFS"
    assert body["fields"][0]["section"] == {"id": sec["id"]}
    item = existing(
        [{"id": "f1", "label": "key", "type": "CONCEALED", "value": "v1", "section": {"id": "s1"}}],
        sections=[{"id": "s1", "label": "ZFS"}],
    )
    assert op.build_plan(item, s)[0] == "ok"


# --- spec validation -------------------------------------------------------


@pytest.mark.parametrize("bad", [
    spec(category="spaceship"),
    spec(title=""),
    spec(fields=[{"type": "concealed", "generate": "on_create"}]),
    spec(fields=[{"label": "token", "type": "wat", "generate": "on_create"}]),
    spec(fields=[{"label": "token", "type": "concealed"}]),
    spec(fields=[{"label": "token", "type": "concealed", "generate": "sometimes"}]),
    spec(fields=[{"label": "token", "type": "concealed", "generate": "always", "value": "x"}]),
    spec(fields=[
        {"label": "a", "type": "concealed", "generate": "on_create"},
        {"label": "A", "type": "concealed", "generate": "on_create"},
    ]),
])
def test_bad_specs_are_rejected(bad):
    with pytest.raises(op.SpecError):
        op.build_plan(None, bad)


# --- apply -----------------------------------------------------------------


def test_apply_creates_then_second_run_is_ok_with_no_writes():
    client = FakeClient()
    first = op.apply_spec(client, {"items": [spec()]})
    assert first["changed"] is True
    assert first["items"][0]["action"] == "created"
    second = op.apply_spec(client, {"items": [spec()]})
    assert second["changed"] is False
    assert second["items"][0]["action"] == "ok"
    assert client.writes == [("create", "External - Test")]


def test_apply_check_mode_writes_nothing_but_reports_changes():
    client = FakeClient()
    result = op.apply_spec(client, {"items": [spec()]}, check=True)
    assert result["changed"] is True and result["items"][0]["action"] == "created"
    assert client.writes == []


def test_apply_updates_an_existing_item():
    client = FakeClient([existing([])])
    result = op.apply_spec(client, {"items": [spec()]})
    assert result["items"][0]["action"] == "updated"
    assert client.writes == [("replace", "External - Test")]


def test_result_never_contains_a_value():
    client = FakeClient()
    s = spec(fields=[
        {"label": "token", "type": "concealed", "value": SECRET},
        {"label": "gen", "type": "concealed", "generate": "on_create"},
    ])
    result = op.apply_spec(client, {"items": [s]})
    text = json.dumps(result)
    assert SECRET not in text and GENERATED not in text


def test_validation_runs_before_any_write():
    client = FakeClient()
    with pytest.raises(op.SpecError):
        op.apply_spec(client, {"items": [spec(), spec(category="nope")]})
    assert client.writes == []


def test_two_items_with_one_title_in_a_spec_are_rejected():
    with pytest.raises(op.SpecError, match="twice"):
        op.apply_spec(FakeClient(), {"items": [spec(), spec()]})


# --- CLI wiring ------------------------------------------------------------


def test_main_apply_reads_stdin_and_prints_json_without_values(monkeypatch, capsys):
    import io

    fake = FakeClient()
    monkeypatch.setattr(op, "_client", lambda token_env: fake)
    payload = {"items": [spec(fields=[{"label": "token", "type": "concealed", "value": SECRET}])]}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    assert op.main(["apply", "-", "--json"]) == 0
    out = capsys.readouterr().out
    assert json.loads(out)["items"][0]["action"] == "created"
    assert SECRET not in out


def test_main_apply_reports_a_bad_spec_on_stderr_with_exit_2(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(op, "_client", lambda token_env: FakeClient())
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"items": [spec(category="nope")]}))
    assert op.main(["apply", str(path)]) == 2
    captured = capsys.readouterr()
    assert "category" in captured.err and captured.out == ""
