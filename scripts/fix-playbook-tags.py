#!/usr/bin/env python3
"""Add missing type and role-name tags to all custom roles in all playbooks."""

import re
import sys
from pathlib import Path
import ruamel.yaml

PLAYBOOKS_DIR = Path(__file__).parent.parent / "playbooks"


def is_galaxy_role(role_name: str) -> bool:
    return "." in role_name


def get_type_tag(role_name: str) -> str:
    return role_name.split("-")[0]


def fix_tags(current_tags, role_name: str) -> list[str]:
    """Return corrected tag list with type and role-name tags present."""
    if current_tags is None:
        tags = []
    elif isinstance(current_tags, str):
        tags = [current_tags]
    else:
        tags = list(current_tags)

    # Fix compositions -> composition
    tags = ["composition" if t == "compositions" else t for t in tags]

    # Fix known typo
    tags = [
        "composition-container-management"
        if t == "composition-container-managements"
        else t
        for t in tags
    ]

    type_tag = get_type_tag(role_name)

    if type_tag not in tags and type_tag != role_name:
        tags.insert(0, type_tag)

    if role_name not in tags:
        tags.append(role_name)

    return tags


def needs_update(current_tags, role_name: str) -> bool:
    """Check if tags need updating without modifying anything."""
    if current_tags is None:
        tags = []
    elif isinstance(current_tags, str):
        tags = [current_tags]
    else:
        tags = list(current_tags)

    if "compositions" in tags:
        return True
    if "composition-container-managements" in tags:
        return True
    type_tag = get_type_tag(role_name)
    if type_tag not in tags:
        return True
    if role_name not in tags:
        return True
    return False


def process_file(path: Path, dry_run: bool = False) -> bool:
    import re

    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.best_sequence_indent = 4
    yaml.best_sequence_dash_offset = 2

    with open(path, encoding="utf-8") as f:
        content = f.read()
    had_explicit_start = content.strip().startswith("---")
    if had_explicit_start:
        yaml.explicit_start = True
    data = yaml.load(content)

    if not isinstance(data, list):
        return False

    modified = False
    for play in data:
        if not isinstance(play, dict) or "roles" not in play:
            continue
        roles = play["roles"]
        if not isinstance(roles, list):
            continue
        for role_entry in roles:
            if not isinstance(role_entry, dict):
                continue
            role_name = role_entry.get("role")
            if not role_name or is_galaxy_role(role_name):
                continue

            current_tags = role_entry.get("tags")
            if not needs_update(current_tags, role_name):
                continue

            new_tags = fix_tags(current_tags, role_name)

            if dry_run:
                if current_tags is None:
                    old_list = []
                elif isinstance(current_tags, str):
                    old_list = [current_tags]
                else:
                    old_list = list(current_tags)
                print(f"  {role_name}: {old_list} -> {new_tags}")
            else:
                seq = ruamel.yaml.comments.CommentedSeq(new_tags)
                seq.fa.set_flow_style()
                role_entry["tags"] = seq

            modified = True

    if modified and not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

        # Post-process: remove blank lines ruamel.yaml inserts between role: and tags:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        # Collapse blank line between "  - role: ..." and the next non-blank line
        fixed = re.sub(r'(\n([ \t]+-[ \t]+role:[ \t]+\S[^\n]*))\n\n+([ \t]+\S)', r'\1\n\3', text)
        # Collapse any remaining triple+ newlines down to double
        while '\n\n\n' in fixed:
            fixed = fixed.replace('\n\n\n', '\n\n')
        with open(path, "w", encoding="utf-8") as f:
            f.write(fixed)

    return modified


def main():
    dry_run = "--dry-run" in sys.argv
    playbooks = sorted(PLAYBOOKS_DIR.rglob("*.yaml"))
    changed = []

    for path in playbooks:
        # Quick pre-check to avoid loading YAML for files with no issues
        yaml = ruamel.yaml.YAML()
        yaml.preserve_quotes = True
        yaml.width = 4096
        with open(path, encoding="utf-8") as f:
            data = yaml.load(f)

        if not isinstance(data, list):
            continue

        file_has_changes = False
        for play in data:
            if not isinstance(play, dict) or "roles" not in play:
                continue
            for role_entry in play.get("roles", []):
                if not isinstance(role_entry, dict):
                    continue
                role_name = role_entry.get("role")
                if not role_name or is_galaxy_role(role_name):
                    continue
                if needs_update(role_entry.get("tags"), role_name):
                    file_has_changes = True
                    break
            if file_has_changes:
                break

        if not file_has_changes:
            continue

        rel = path.relative_to(PLAYBOOKS_DIR.parent)
        if dry_run:
            print(f"\n{rel}")

        if process_file(path, dry_run=dry_run):
            changed.append(path)
            if not dry_run:
                print(f"Updated: {rel}")

    verb = "Would update" if dry_run else "Updated"
    print(f"\n{verb} {len(changed)} file(s).")


if __name__ == "__main__":
    main()
