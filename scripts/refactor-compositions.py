#!/usr/bin/env python3
"""
Automate refactoring of composition-* roles to use composition-common dependency.

This script:
1. Finds all composition-* roles (excluding _TEMPLATE and composition-common)
2. Checks if already refactored (has meta/main.yaml with composition-common)
3. For unrefactored roles:
   - Adds composition_name to defaults/main.yaml
   - Creates meta/main.yaml with composition-common dependency
   - Adds Docker Compose startup task to tasks/main.yaml
4. Reports results and flags any issues for manual review
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# Configuration
ROLES_DIR = Path(__file__).parent.parent / "ansible" / "roles"
SKIP_ROLES = {"composition-_TEMPLATE", "composition-common"}

# Templates
META_TEMPLATE = """dependencies:
  - role: composition-common
    vars:
      composition_name: {composition_name}
"""

DEFAULTS_HEADER = """# Composition name (used by composition-common dependency)
composition_name: {composition_name}

"""

DOCKER_COMPOSE_TASK = """
# ----------------------------
# Start composition
# ----------------------------

- name: Start Docker Compose project
  community.docker.docker_compose_v2:
    project_src: "{{ composition_root }}"
    state: present
    build: always
    remove_orphans: true
"""


class RefactoringResult:
    def __init__(self):
        self.skipped: List[Tuple[str, str]] = []  # (role, reason)
        self.already_refactored: List[str] = []
        self.refactored: List[str] = []
        self.errors: List[Tuple[str, str]] = []  # (role, error)
        self.needs_manual: List[Tuple[str, str]] = []  # (role, reason)


def get_composition_name(role_dir_name: str) -> str:
    """Extract composition name from role directory name."""
    return role_dir_name.replace("composition-", "")


def is_already_refactored(role_path: Path) -> bool:
    """Check if role has already been refactored."""
    meta_file = role_path / "meta" / "main.yaml"
    if not meta_file.exists():
        return False

    content = meta_file.read_text()
    return "composition-common" in content


def has_tasks_file(role_path: Path) -> bool:
    """Check if role has tasks/main.yaml file."""
    return (role_path / "tasks" / "main.yaml").exists()


def add_composition_name_to_defaults(role_path: Path, composition_name: str) -> None:
    """Add composition_name to the top of defaults/main.yaml."""
    defaults_file = role_path / "defaults" / "main.yaml"

    # Ensure defaults directory exists
    defaults_file.parent.mkdir(exist_ok=True)

    if defaults_file.exists():
        content = defaults_file.read_text()
        # Check if composition_name is already defined
        if re.search(r'^composition_name:', content, re.MULTILINE):
            return  # Already has it

        # Prepend composition_name
        new_content = DEFAULTS_HEADER.format(composition_name=composition_name) + content
    else:
        # Create new defaults file
        new_content = DEFAULTS_HEADER.format(composition_name=composition_name).rstrip() + "\n"

    defaults_file.write_text(new_content)


def create_meta_file(role_path: Path, composition_name: str) -> None:
    """Create meta/main.yaml with composition-common dependency."""
    meta_file = role_path / "meta" / "main.yaml"

    # Ensure meta directory exists
    meta_file.parent.mkdir(exist_ok=True)

    content = META_TEMPLATE.format(composition_name=composition_name)
    meta_file.write_text(content)


def add_docker_compose_task(role_path: Path) -> Tuple[bool, str]:
    """
    Add Docker Compose startup task to tasks/main.yaml.

    Returns:
        (success, message) - message explains if manual review needed
    """
    tasks_file = role_path / "tasks" / "main.yaml"

    if not tasks_file.exists():
        return False, "No tasks/main.yaml file found"

    content = tasks_file.read_text()

    # Check if Docker Compose task already exists
    if "docker_compose_v2:" in content or "Start Docker Compose project" in content:
        return True, "Docker Compose task already exists"

    # Check if file ends with newline
    if not content.endswith("\n"):
        content += "\n"

    # Append Docker Compose task
    new_content = content + DOCKER_COMPOSE_TASK
    tasks_file.write_text(new_content)

    return True, "Added Docker Compose task"


def refactor_role(role_path: Path, composition_name: str) -> Tuple[bool, str]:
    """
    Refactor a single role.

    Returns:
        (success, message)
    """
    try:
        # Step 1: Add composition_name to defaults
        add_composition_name_to_defaults(role_path, composition_name)

        # Step 2: Create meta file
        create_meta_file(role_path, composition_name)

        # Step 3: Add Docker Compose task
        success, msg = add_docker_compose_task(role_path)
        if not success:
            return False, f"Failed to add Docker Compose task: {msg}"

        return True, msg

    except Exception as e:
        return False, str(e)


def main():
    result = RefactoringResult()

    # Find all composition roles
    composition_roles = sorted([
        d for d in ROLES_DIR.iterdir()
        if d.is_dir() and d.name.startswith("composition-")
    ])

    print(f"Found {len(composition_roles)} composition roles")
    print("=" * 60)

    for role_path in composition_roles:
        role_name = role_path.name

        # Skip excluded roles
        if role_name in SKIP_ROLES:
            result.skipped.append((role_name, "Excluded from refactoring"))
            continue

        # Check if already refactored
        if is_already_refactored(role_path):
            result.already_refactored.append(role_name)
            continue

        # Check if role has tasks file
        if not has_tasks_file(role_path):
            result.needs_manual.append((role_name, "No tasks/main.yaml file"))
            continue

        # Perform refactoring
        composition_name = get_composition_name(role_name)
        success, message = refactor_role(role_path, composition_name)

        if success:
            result.refactored.append(role_name)
            print(f"✓ {role_name}: {message}")
        else:
            result.errors.append((role_name, message))
            print(f"✗ {role_name}: {message}")

    # Print summary
    print("\n" + "=" * 60)
    print("REFACTORING SUMMARY")
    print("=" * 60)

    print(f"\n✓ Successfully refactored: {len(result.refactored)}")
    for role in result.refactored:
        print(f"  - {role}")

    print(f"\n→ Already refactored: {len(result.already_refactored)}")
    for role in result.already_refactored:
        print(f"  - {role}")

    print(f"\n⊘ Skipped: {len(result.skipped)}")
    for role, reason in result.skipped:
        print(f"  - {role}: {reason}")

    if result.needs_manual:
        print(f"\n⚠ Needs manual review: {len(result.needs_manual)}")
        for role, reason in result.needs_manual:
            print(f"  - {role}: {reason}")

    if result.errors:
        print(f"\n✗ Errors: {len(result.errors)}")
        for role, error in result.errors:
            print(f"  - {role}: {error}")

    print("\n" + "=" * 60)
    total_processed = len(result.refactored) + len(result.already_refactored)
    total_roles = len(composition_roles) - len(result.skipped)
    print(f"Total: {total_processed}/{total_roles} roles refactored")

    if result.needs_manual or result.errors:
        print("\n⚠ Some roles need manual attention (see above)")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
