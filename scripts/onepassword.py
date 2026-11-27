#!/usr/bin/env python3
"""Manage items in the 1Password Infra vault through Connect. stdlib only.

    onepassword.py apply SPEC.json|-  [--check] [--json]   create/update items
    onepassword.py audit                                    audit vault vs repo
    onepassword.py inspect                                  item shapes, no values

`apply` reads a JSON spec (from a file or stdin) and makes the vault match it,
the way the onepassword.connect collection's generic_item does:

  {"items": [{"title": "External - X", "category": "secure_note",
              "tags": ["external", "ansible"], "urls": [],
              "fields": [
                {"label": "token", "type": "concealed", "generate": "on_create"},
                {"label": "username", "value": "someone"}]}]}

- generate: "on_create" makes the value in 1Password (it never reaches this
  process) and leaves an existing field alone, so a second run is `ok`.
  "always" regenerates every run (for rotation). Default recipe: 32 characters,
  letters and digits (symbols: true to add them).
- value: sets the field; unchanged values are `ok`.
- Fields not in the spec (including Notes) are kept; tags and urls are unioned.
- A category cannot be changed after creation: a mismatch is an error.
Output names items and fields only, never a value.

Environment: OP_CONNECT_HOST, OP_CONNECT_VAULT, and the token in
OP_CONNECT_TOKEN_WRITE (apply) or OP_CONNECT_TOKEN (audit, inspect).
"""

import argparse
import copy
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "plugins" / "lookup"))

from op_connect_client import OpConnectClient, OpConnectError  # noqa: E402


class SpecError(Exception):
    pass


CATEGORIES = {
    "login", "password", "server", "database", "api_credential", "secure_note",
    "software_license", "wireless_router", "bank_account", "email_account",
    "credit_card", "membership", "passport", "outdoor_license", "driver_license",
    "identity", "reward_program", "social_security_number",
}
TYPES = {"string", "concealed", "email", "url", "otp", "date", "month_year"}
GENERATE = {None, "never", "on_create", "always"}
# Each category's built-in fields, found by probing Connect: Login and Password
# items need `purpose` (without it Connect adds duplicate, empty built-ins);
# Server items reject `purpose` and take the field id instead.
BUILTIN_PURPOSE = {"login": {"username": "USERNAME", "password": "PASSWORD"}, "password": {"password": "PASSWORD"}}
BUILTIN_ID = {"server": {"username", "password"}}
DEFAULT_LENGTH = 32


def _recipe(raw):
    raw = raw or {}
    sets = []
    if raw.get("letters", True):
        sets.append("LETTERS")
    if raw.get("digits", True):
        sets.append("DIGITS")
    if raw.get("symbols", False):
        sets.append("SYMBOLS")
    return {"length": int(raw.get("length", DEFAULT_LENGTH)), "characterSets": sets}


def validate_item(raw):
    """Normalise one spec item, or raise SpecError (names only, never values)."""
    title = raw.get("title")
    if not isinstance(title, str) or not title.strip():
        raise SpecError("item without a title")
    category = str(raw.get("category", "")).lower()
    if category not in CATEGORIES:
        raise SpecError(f"'{title}': unknown category '{raw.get('category')}'")
    fields, seen = [], set()
    for f in raw.get("fields") or []:
        label = f.get("label")
        if not isinstance(label, str) or not label.strip():
            raise SpecError(f"'{title}': field without a label")
        ftype = str(f.get("type", "string")).lower()
        if ftype not in TYPES:
            raise SpecError(f"'{title}' / '{label}': unknown type '{f.get('type')}'")
        gen = f.get("generate")
        if gen not in GENERATE:
            raise SpecError(f"'{title}' / '{label}': generate must be on_create, always or never")
        gen = None if gen == "never" else gen
        value = f.get("value")
        if gen and value is not None:
            raise SpecError(f"'{title}' / '{label}': generate and value are mutually exclusive")
        if not gen and (not isinstance(value, str) or value == ""):
            raise SpecError(f"'{title}' / '{label}': needs a non-empty value or generate")
        key = (label.lower(), f.get("section"))
        if key in seen:
            raise SpecError(f"'{title}': field '{label}' listed twice")
        seen.add(key)
        fields.append({"label": label, "type": ftype.upper(), "generate": gen, "value": value,
                       "section": f.get("section"), "recipe": _recipe(f.get("recipe"))})
    return {"title": title, "category": category.upper(),
            "purposes": BUILTIN_PURPOSE.get(category, {}), "ids": BUILTIN_ID.get(category, set()),
            "tags": list(raw.get("tags") or []), "urls": list(raw.get("urls") or []), "fields": fields}


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "section"


def _section_id(item, label, create=True):
    for section in item.setdefault("sections", []):
        if section.get("label", "").lower() == label.lower():
            return section["id"]
    if not create:
        return None
    sid = _slug(label)
    item["sections"].append({"id": sid, "label": label})
    return sid


def _new_field(spec_field, item, spec):
    field = {"label": spec_field["label"], "type": spec_field["type"]}
    label = spec_field["label"].lower()
    if label in spec["purposes"]:
        field["purpose"] = spec["purposes"][label]
    elif label in spec["ids"]:
        field["id"] = label
    if spec_field["section"]:
        field["section"] = {"id": _section_id(item, spec_field["section"])}
    if spec_field["generate"]:
        field["generate"] = True
        field["recipe"] = spec_field["recipe"]
    else:
        field["value"] = spec_field["value"]
    return field


def build_plan(existing, raw_spec):
    """(action, body, changes). action: created | updated | ok. body is what to
    send (None when ok). changes name fields only, never values."""
    spec = validate_item(raw_spec)
    changes = []
    if existing is None:
        item = {"title": spec["title"], "category": spec["category"], "tags": spec["tags"], "fields": []}
        if spec["urls"]:
            item["urls"] = [{"href": u, "primary": i == 0} for i, u in enumerate(spec["urls"])]
        for sf in spec["fields"]:
            item["fields"].append(_new_field(sf, item, spec))
            changes.append({"label": sf["label"], "change": "generated" if sf["generate"] else "added"})
        return "created", item, changes

    if str(existing.get("category", "")).upper() != spec["category"]:
        raise SpecError(
            f"'{spec['title']}': category is {existing.get('category')}, spec says {spec['category']};"
            " a category cannot be changed, recreate the item"
        )
    item = copy.deepcopy(existing)
    item.setdefault("fields", [])
    for sf in spec["fields"]:
        sid = _section_id(item, sf["section"], create=False) if sf["section"] else None
        match = next(
            (
                f for f in item["fields"]
                if f.get("label", "").lower() == sf["label"].lower()
                and ((f.get("section") or {}).get("id") == sid if sf["section"] else not f.get("section"))
            ),
            None,
        )
        if match is None:
            item["fields"].append(_new_field(sf, item, spec))
            changes.append({"label": sf["label"], "change": "generated" if sf["generate"] else "added"})
        elif sf["generate"] == "always":
            match.pop("value", None)
            match["generate"] = True
            match["recipe"] = sf["recipe"]
            changes.append({"label": sf["label"], "change": "regenerated"})
        elif sf["generate"] == "on_create":
            continue
        elif match.get("value") != sf["value"]:
            match["value"] = sf["value"]
            changes.append({"label": sf["label"], "change": "updated"})
    tags = list(item.get("tags") or [])
    new_tags = [t for t in spec["tags"] if t not in tags]
    if new_tags:
        item["tags"] = tags + new_tags
        changes.append({"label": "(tags)", "change": "updated"})
    urls = item.get("urls") or []
    new_urls = [u for u in spec["urls"] if u not in [x.get("href") for x in urls]]
    if new_urls:
        item["urls"] = urls + [{"href": u, "primary": not urls and i == 0} for i, u in enumerate(new_urls)]
        changes.append({"label": "(urls)", "change": "updated"})
    return ("updated", item, changes) if changes else ("ok", None, [])


def apply_spec(client, spec, check=False):
    items = spec.get("items") or []
    titles = [i.get("title") for i in items]
    for title in titles:
        if titles.count(title) > 1:
            raise SpecError(f"'{title}' appears twice in the spec")
    for item in items:  # validate everything before the first write
        validate_item(item)
    results = []
    for raw in items:
        action, body, changes = build_plan(client.find_item(raw["title"]), raw)
        item_id = (body or {}).get("id")
        if body is not None and not check:
            reply = client.create_item(body) if action == "created" else client.replace_item(body)
            item_id = reply.get("id", item_id)
        results.append({"title": raw["title"], "action": action, "id": item_id, "fields": changes})
    return {"changed": any(r["action"] != "ok" for r in results), "check": check, "items": results}


# --- CLI -------------------------------------------------------------------


def _client(token_env):
    return OpConnectClient(
        os.environ.get("OP_CONNECT_HOST", ""),
        os.environ.get(token_env, ""),
        os.environ.get("OP_CONNECT_VAULT", ""),
    )


def cmd_apply(args):
    try:
        text = sys.stdin.read() if args.spec == "-" else Path(args.spec).read_text()
        result = apply_spec(_client("OP_CONNECT_TOKEN_WRITE"), json.loads(text), check=args.check)
    except (SpecError, OpConnectError, ValueError, OSError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result))
    else:
        for r in result["items"]:
            names = ", ".join(f"{c['label']} ({c['change']})" for c in r["fields"])
            print(f"{r['action']}{' (check)' if args.check and r['action'] != 'ok' else ''}: {r['title']}"
                  + (f" [{names}]" if names else ""))
    return 0


def cmd_inspect(args):
    try:
        for item in _client(args.token_env).item_metadata():
            labels = [f["label"] or f["id"] for f in item["fields"] if f["has_value"]]
            print(f"{item['title']} | {item['category']} | {item['tags']} | {labels}")
    except OpConnectError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2
    return 0


SCAN_DIRS = ["roles", "playbooks", "inventory", "scripts"]
SKIP_NAMES = {"onepassword.py", "audit-secrets.yaml", "provision-secrets.yaml"}


def _repo_files():
    for directory in SCAN_DIRS:
        for path in (REPO / directory).rglob("*"):
            if not path.is_file() or path.name in SKIP_NAMES or path.name.startswith("vault_"):
                continue
            if "__pycache__" in path.parts or path.suffix in {".pyc", ".png", ".jpg", ".ico"}:
                continue
            yield path


def cmd_audit(args):
    from op_audit import audit, find_references

    try:
        items = _client(args.token_env).item_metadata()
    except OpConnectError as err:
        print(f"ERROR: {err}")
        return 2
    refs, corpus = [], []
    for path in _repo_files():
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        refs.extend(find_references(text, str(path.relative_to(REPO))))
        corpus.append(text)
    result = audit(items, refs, "\n".join(corpus))
    print(f"{len(items)} items, {len(refs)} lookups in the repo")
    for line in result["errors"]:
        print(f"ERROR: {line}")
    for line in result["warnings"]:
        print(f"WARNING: {line}")
    if not result["errors"]:
        print("No errors.")
    return 1 if result["errors"] else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("apply", help="create or update items from a JSON spec")
    p.add_argument("spec", help="spec file, or - for stdin")
    p.add_argument("--check", action="store_true", help="plan only; write nothing")
    p.add_argument("--json", action="store_true", help="print the result as JSON")
    p.set_defaults(func=cmd_apply)
    for name, func in (("audit", cmd_audit), ("inspect", cmd_inspect)):
        q = sub.add_parser(name)
        q.add_argument("--token-env", default="OP_CONNECT_TOKEN", help="variable holding the token")
        q.set_defaults(func=func)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
