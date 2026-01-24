#!/usr/bin/env python3
"""
Update playbooks to use direct composition role inclusion instead of the compositions role.

This script:
1. Reads host_vars files to extract compositions lists for each host
2. Finds playbooks that use '- role: compositions'
3. Replaces with individual composition-* role inclusions
4. Preserves indentation and formatting
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional

# Configuration
INVENTORY_DIR = Path(__file__).parent.parent / "ansible" / "inventory"
PLAYBOOKS_DIR = Path(__file__).parent.parent / "ansible" / "playbooks"


def load_host_compositions(host_name: str) -> Optional[List[str]]:
    """Load compositions list from host_vars file."""
    host_vars_file = INVENTORY_DIR / "host_vars" / host_name / "core.yaml"

    if not host_vars_file.exists():
        return None

    try:
        with open(host_vars_file) as f:
            data = yaml.safe_load(f)

        compositions = data.get("compositions", [])
        return compositions if compositions else None
    except Exception as e:
        print(f"Warning: Failed to load {host_vars_file}: {e}")
        return None


def extract_host_from_playbook(playbook_path: Path) -> Optional[str]:
    """Extract the host name from a playbook file."""
    try:
        with open(playbook_path) as f:
            data = yaml.safe_load(f)

        if not data:
            return None

        # Get first play's hosts value
        if isinstance(data, list) and len(data) > 0:
            hosts_value = data[0].get("hosts")
            if hosts_value:
                return hosts_value

        return None
    except Exception as e:
        print(f"Warning: Failed to parse {playbook_path}: {e}")
        return None


def find_compositions_role_line(lines: List[str]) -> Optional[int]:
    """Find the line number where '- role: compositions' appears."""
    for i, line in enumerate(lines):
        if re.match(r'^\s*-\s+role:\s+compositions\s*$', line):
            return i
    return None


def get_indentation(line: str) -> str:
    """Extract the indentation from a line."""
    match = re.match(r'^(\s*)', line)
    return match.group(1) if match else ""


def replace_compositions_role(playbook_path: Path, compositions: List[str]) -> bool:
    """
    Replace '- role: compositions' with individual composition roles.

    Returns:
        True if modified, False otherwise
    """
    with open(playbook_path) as f:
        lines = f.readlines()

    # Find the compositions role line
    role_line_num = find_compositions_role_line(lines)
    if role_line_num is None:
        return False

    # Get the indentation from the original line
    indent = get_indentation(lines[role_line_num])

    # Build replacement lines
    replacement_lines = []
    for comp in compositions:
        replacement_lines.append(f"{indent}- role: composition-{comp}\n")

    # Replace the line
    new_lines = lines[:role_line_num] + replacement_lines + lines[role_line_num + 1:]

    # Write back
    with open(playbook_path, 'w') as f:
        f.writelines(new_lines)

    return True


def main():
    # Find all playbooks that use 'role: compositions'
    playbooks_with_compositions = []

    for playbook in PLAYBOOKS_DIR.rglob("*.yaml"):
        with open(playbook) as f:
            content = f.read()

        if re.search(r'^\s*-\s+role:\s+compositions\s*$', content, re.MULTILINE):
            playbooks_with_compositions.append(playbook)

    print(f"Found {len(playbooks_with_compositions)} playbooks using 'compositions' role")
    print("=" * 60)

    modified = 0
    skipped = 0
    errors = 0

    for playbook in sorted(playbooks_with_compositions):
        # Extract host from playbook
        host = extract_host_from_playbook(playbook)

        if not host:
            print(f"⊘ {playbook.relative_to(PLAYBOOKS_DIR)}: Could not determine host")
            skipped += 1
            continue

        # Load compositions for this host
        compositions = load_host_compositions(host)

        if not compositions:
            print(f"⊘ {playbook.relative_to(PLAYBOOKS_DIR)}: No compositions defined for {host}")
            skipped += 1
            continue

        # Replace compositions role with individual roles
        try:
            if replace_compositions_role(playbook, compositions):
                print(f"✓ {playbook.relative_to(PLAYBOOKS_DIR)}: {host} → {len(compositions)} roles")
                modified += 1
            else:
                print(f"⊘ {playbook.relative_to(PLAYBOOKS_DIR)}: No compositions role found")
                skipped += 1
        except Exception as e:
            print(f"✗ {playbook.relative_to(PLAYBOOKS_DIR)}: {e}")
            errors += 1

    # Summary
    print("\n" + "=" * 60)
    print("UPDATE SUMMARY")
    print("=" * 60)
    print(f"✓ Modified: {modified}")
    print(f"⊘ Skipped: {skipped}")
    print(f"✗ Errors: {errors}")
    print()

    if errors > 0:
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
