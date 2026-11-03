from op_audit import audit, find_references


def item(title, tags, category="SECURE_NOTE", fields=()):
    return {"id": title, "title": title, "category": category, "tags": list(tags),
            "fields": [{"id": f, "label": f, "has_value": v} for f, v in fields]}


def errors(items, refs=(), corpus=""):
    return audit(items, list(refs), corpus)["errors"]


def warnings(items, refs=(), corpus=""):
    return audit(items, list(refs), corpus)["warnings"]


def test_clean_set_has_no_findings():
    items = [item("App - Karakeep", ["app"]), item("Infra - Grafana", ["login"], "LOGIN"), item("Host - Camina", ["host"], "SERVER")]
    assert audit(items, [], "") == {"errors": [], "warnings": []}


def test_item_without_group_tag():
    assert errors([item("App - X", [])]) == ["App - X: no group tag"]


def test_item_with_two_group_tags():
    assert errors([item("App - X", ["app", "host"])]) == ["App - X: several group tags (app, host)"]


def test_title_prefix_must_match_group():
    assert errors([item("Server - X", ["host"], "SERVER")]) == ["Server - X: title should start with 'Host - ' (group host)"]


def test_login_group_uses_infra_prefix():
    assert errors([item("Infra - Grafana", ["login"], "LOGIN")]) == []
    assert errors([item("Login - Grafana", ["login"], "LOGIN")]) == ["Login - Grafana: title should start with 'Infra - ' (group login)"]


def test_duplicate_titles():
    items = [item("Host - Camina", ["host"], "SERVER"), item("Host - Camina", ["host"], "SERVER")]
    assert "Host - Camina: 2 items share this title" in errors(items)


def test_category_mismatch_is_a_warning_not_an_error():
    items = [item("External - GitHub", ["external"], "API_CREDENTIAL")]
    assert errors(items) == []
    assert warnings(items) == ["External - GitHub: category API_CREDENTIAL, expected SECURE_NOTE"]


def test_extra_tag_is_a_warning():
    assert warnings([item("App - X", ["app", "old-tag"])]) == ["App - X: unexpected tag 'old-tag'"]


def test_reference_to_missing_item():
    assert errors([], [("App - Nope", "token", "roles/x/onepassword_x.yaml")]) == ["roles/x/onepassword_x.yaml: item 'App - Nope' not found"]


def test_reference_to_missing_field():
    items = [item("App - X", ["app", "ansible"], fields=[("token", False)])]
    assert errors(items, [("App - X", "other", "m.yaml")]) == ["m.yaml: item 'App - X' has no field 'other'"]


def test_reference_to_builtin_by_id():
    items = [item("Host - Camina", ["host", "ansible"], "SERVER", fields=[("password", True)])]
    assert errors(items, [("Host - Camina", "password", "m.yaml")]) == []


def test_referenced_item_needs_ansible_tag():
    items = [item("App - X", ["app"], fields=[("token", True)])]
    assert errors(items, [("App - X", "token", "m.yaml")]) == ["App - X: read by m.yaml but not tagged 'ansible'"]


def test_ansible_field_without_consumer():
    items = [item("App - X", ["app", "ansible"], fields=[("token", True), ("spare", True)])]
    assert errors(items, [("App - X", "token", "m.yaml")]) == ["App - X / spare: no consumer in the repo"]


def test_label_found_in_repo_text_counts_as_consumer():
    items = [item("External - GitHub", ["external", "ansible"], fields=[("gateway_issues_token", True)])]
    assert errors(items, [], "token_field: gateway_issues_token") == []


def test_empty_fields_need_no_consumer():
    items = [item("App - X", ["app", "ansible"], fields=[("placeholder", False)])]
    assert errors(items) == []


def test_untagged_ansible_items_are_not_checked_for_consumers():
    items = [item("App - X", ["app"], fields=[("token", True)])]
    assert errors(items) == []


def test_builtin_labels_need_an_explicit_reference():
    items = [item("Host - X", ["host", "ansible"], "SERVER", fields=[("password", True)])]
    assert errors(items, [], "password everywhere") == ["Host - X / password: no consumer in the repo"]


def test_find_references():
    text = """
    a: "{{ lookup('onepassword_connect', 'External - GitHub', 'stars token') }}"
    b: "{{ lookup("onepassword_connect", "Host - Camina", "password", vault="Infra") }}"
    c: not a lookup
    """
    assert find_references(text, "m.yaml") == [("External - GitHub", "stars token", "m.yaml"), ("Host - Camina", "password", "m.yaml")]


def test_label_inside_a_longer_name_is_not_a_consumer():
    items = [item("External - GitHub", ["external", "ansible"], fields=[("github2karakeep_token", True)])]
    assert errors(items, [], "x: {{ vault_github2karakeep_token }}") == ["External - GitHub / github2karakeep_token: no consumer in the repo"]


def test_label_with_spaces_found_quoted():
    items = [item("External - Enable Banking", ["external", "ansible"], fields=[("App ID", True)])]
    assert errors(items, [], "selectattr('label', 'eq', 'App ID')") == []
