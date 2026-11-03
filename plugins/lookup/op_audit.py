"""Checks on the 1Password Infra vault against the naming scheme and the repo.

Pure Python, no Ansible imports. Works on metadata only (titles, tags, field
labels), never values, so its output is safe to print.
"""

import re

# group tag: (title prefix, category). Login items are prefixed 'Infra'.
GROUPS = {
    "app": ("App - ", "SECURE_NOTE"),
    "login": ("Infra - ", "LOGIN"),
    "host": ("Host - ", "SERVER"),
    "hardware": ("Hardware - ", "SECURE_NOTE"),
    "external": ("External - ", "SECURE_NOTE"),
}
BUILTIN_LABELS = {"username", "password", "notesPlain"}

_LOOKUP = re.compile(
    r"""lookup\(\s*(['"])onepassword_connect\1\s*,\s*(['"])(.+?)\2\s*,\s*(['"])(.+?)\4"""
)


def find_references(text, source):
    """(title, field, source) for each lookup('onepassword_connect', ...) in text."""
    return [(m.group(3), m.group(5), source) for m in _LOOKUP.finditer(text)]


def _in_text(label, corpus):
    """label as a whole word, so 'github_token' does not match 'vault_github_token'."""
    return re.search(r"(?<![A-Za-z0-9_])" + re.escape(label) + r"(?![A-Za-z0-9_])", corpus) is not None


def _has_field(item, name):
    return any(name in (f["label"], f["id"]) for f in item["fields"])


def audit(items, refs, corpus):
    errors, warnings = [], []
    by_title = {}
    for it in items:
        by_title.setdefault(it["title"], []).append(it)

    for title, same in by_title.items():
        if len(same) > 1:
            errors.append(f"{title}: {len(same)} items share this title")

    for it in items:
        title, tags = it["title"], it["tags"]
        group_tags = [t for t in tags if t in GROUPS]
        if not group_tags:
            errors.append(f"{title}: no group tag")
            continue
        if len(group_tags) > 1:
            errors.append(f"{title}: several group tags ({', '.join(group_tags)})")
            continue
        group = group_tags[0]
        prefix, category = GROUPS[group]
        if not title.startswith(prefix):
            errors.append(f"{title}: title should start with '{prefix}' (group {group})")
        if it["category"] != category:
            warnings.append(f"{title}: category {it['category']}, expected {category}")
        for tag in tags:
            if tag not in GROUPS and tag != "ansible":
                warnings.append(f"{title}: unexpected tag '{tag}'")

    referenced = {}
    for title, field, source in refs:
        matches = by_title.get(title, [])
        if not matches:
            errors.append(f"{source}: item '{title}' not found")
            continue
        if len(matches) > 1:
            continue  # reported above as a duplicate title
        item = matches[0]
        referenced.setdefault(title, set()).add(field)
        if not _has_field(item, field):
            errors.append(f"{source}: item '{title}' has no field '{field}'")
        if "ansible" not in item["tags"]:
            message = f"{title}: read by {source} but not tagged 'ansible'"
            if message not in errors:
                errors.append(message)

    for it in items:
        if "ansible" not in it["tags"] or len(by_title[it["title"]]) > 1:
            continue
        for field in it["fields"]:
            label = field["label"]
            if not label or not field["has_value"]:
                continue
            if label in referenced.get(it["title"], set()) or field["id"] in referenced.get(it["title"], set()):
                continue
            if label not in BUILTIN_LABELS and _in_text(label, corpus):
                continue
            errors.append(f"{it['title']} / {label}: no consumer in the repo")

    return {"errors": errors, "warnings": warnings}
