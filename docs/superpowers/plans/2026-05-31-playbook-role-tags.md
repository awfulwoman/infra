# Playbook Role Tags Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure every custom role entry in every playbook has both a type tag (e.g. `composition` for `composition-*`) and an exact role-name tag (e.g. `composition-homeassistant`).

**Architecture:** A Python script using `ruamel.yaml` (round-trip mode) processes all playbook YAML files, identifies custom role entries, and adds/fixes tags in-place while preserving all comments and formatting. Galaxy roles (containing `.` in the name) are left untouched.

**Tech Stack:** Python 3, ruamel.yaml (already available)

---

## What "correct" looks like

For a role named `composition-homeassistant`:
- Type tag: `composition` (the prefix before the first `-`)
- Role name tag: `composition-homeassistant`
- Correct: `tags: [composition, composition-homeassistant]`

Type tag mapping:
| Prefix | Type tag |
|---|---|
| `ansible-*` | `ansible` |
| `automation-*` | `automation` |
| `backups-*` | `backups` |
| `bootstrap-*` | `bootstrap` |
| `client-*` | `client` |
| `composition-*` | `composition` |
| `hardware-*` | `hardware` |
| `infra-*` | `infra` |
| `monitoring-*` | `monitoring` |
| `network-*` | `network` |
| `script-*` | `script` |
| `server-*` | `server` |
| `system-*` | `system` |
| `user-*` | `user` |
| `virtual-*` | `virtual` |

## Known bugs to fix (in addition to missing tags)

- `compositions` (plural) → `composition` everywhere
- `composition-container-managements` (typo) → `composition-container-management` in `groups/zfs_backup_servers/core.yaml`
- Empty `tags:` (null) in `hosts/raspberry-pi4-2gb-deedee/terraform.yaml`

## Files in scope (all custom roles with issues)

**Groups:**
- `playbooks/groups/infra/bootstrap.yaml` — missing role name tags
- `playbooks/groups/macos/bootstrap.yaml` — no tags
- `playbooks/groups/personal/workstation-mba2011-ubuntu.yaml` — no tags
- `playbooks/groups/raspberrypi/hardware.yaml` — missing role name tag
- `playbooks/groups/ubuntu/bootstrap.yaml` — no tags
- `playbooks/groups/ubuntu/networking.yaml` — no tags
- `playbooks/groups/zfs_backup_clients/core.yaml` — `compositions` fix, otherwise complete
- `playbooks/groups/zfs_backup_offsite/core.yaml` — `compositions` fix, missing `backups` type on `backups-zfs-archive-offsite`
- `playbooks/groups/zfs_backup_servers/core.yaml` — `compositions` fix, typo fix, missing role name tags

**Hosts:**
- `playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml` — most roles missing role name tags
- `playbooks/hosts/apple-macmini-m4-16gb-malcolm/dev.yaml` — no tags
- `playbooks/hosts/minipc-8gb-homebrain/core.yaml` — `compositions` fix + missing role name tags
- `playbooks/hosts/minipc-8gb-homebrain/dev.yaml` — all roles missing all tags
- `playbooks/hosts/minipc-8gb-homebrain/zfs-api.yaml` — most roles missing all tags
- `playbooks/hosts/minipc-8gb-homebrain/zfs.yaml` — missing role name tags
- `playbooks/hosts/minipc-8gb-test-router/core.yaml` — missing role name tags
- `playbooks/hosts/raspberry-pi4-2gb-deedee/core.yaml` — `compositions` fix + missing role name tags
- `playbooks/hosts/raspberry-pi4-2gb-deedee/dev.yaml` — no tags
- `playbooks/hosts/raspberry-pi4-2gb-deedee/dns.yaml` — no tags
- `playbooks/hosts/raspberry-pi4-2gb-deedee/named-dhcpd.yaml` — no tags
- `playbooks/hosts/raspberry-pi4-2gb-deedee/terraform.yaml` — null tags
- `playbooks/hosts/raspberry-pi4-2gb-deedee/zfs-api.yaml` — most roles missing all tags
- `playbooks/hosts/raspberry-pi4-2gb-deedee/zfs.yaml` — missing role name tags
- `playbooks/hosts/raspberry-pi4-2gb-pikvm/core.yaml` — missing role name tags
- `playbooks/hosts/raspberry-pi4-4gb-albion/core.yaml` — `compositions` fix + missing role name tags
- `playbooks/hosts/raspberry-pi4-4gb-albion/dev.yaml` — no tags
- `playbooks/hosts/raspberry-pi4-4gb-albion/zfs-api.yaml` — most roles missing all tags
- `playbooks/hosts/raspberry-pi4-4gb-albion/zfs.yaml` — missing role name tags
- `playbooks/hosts/raspberry-pi4-4gb-randolph/core.yaml` — `compositions` fix + missing role name tags
- `playbooks/hosts/raspberry-pi5-4gb-belinda/core.yaml` — `compositions` fix + missing role name tags
- `playbooks/hosts/raspberry-pi5-4gb-belinda/dev.yaml` — no tags
- `playbooks/hosts/raspberry-pi5-4gb-belinda/zfs.yaml` — missing role name tags
- `playbooks/hosts/server-64gb-storage/core.yaml` — `compositions` fix + missing role name tags on most
- `playbooks/hosts/server-64gb-storage/downloads.yaml` — no tags
- `playbooks/hosts/server-64gb-storage/email-composition.yaml` — no tags
- `playbooks/hosts/server-64gb-storage/memorybank.yaml` — no tags
- `playbooks/hosts/server-64gb-storage/metrics-and-visuals.yaml` — no tags
- `playbooks/hosts/server-64gb-storage/zfs-api.yaml` — `compositions` fix + missing role name tag
- `playbooks/hosts/server-64gb-storage/zfs.yaml` — missing role name tags
- `playbooks/hosts/server-8gb-backups/core.yaml` — `compositions` fix + missing role name tags
- `playbooks/hosts/server-8gb-backups/dev.yaml` — no tags
- `playbooks/hosts/server-8gb-backups/zfs-api.yaml` — most roles missing all tags
- `playbooks/hosts/server-8gb-backups/zfs.yaml` — missing role name tags
- `playbooks/hosts/vps-hetzner-public01/core.yaml` — `compositions` fix + missing role name tags
- `playbooks/hosts/vps-hetzner-public01/dev.yaml` — missing role name tags

**Utility:**
- `playbooks/utility/deploy-promtail.yaml` — no tags

---

## Task 1: Write the transformation script

**Files:**
- Create: `scripts/fix-playbook-tags.py`

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Add missing type and role-name tags to all custom roles in all playbooks."""

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

    if type_tag not in tags:
        tags.insert(0, type_tag)

    if role_name not in tags:
        tags.append(role_name)

    return tags


def process_file(path: Path, dry_run: bool = False) -> bool:
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096  # Prevent line wrapping

    with open(path) as f:
        data = yaml.load(f)

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
            new_tags = fix_tags(current_tags, role_name)

            if new_tags != (list(current_tags) if current_tags else []):
                if dry_run:
                    print(f"  {role_name}: {current_tags!r} -> {new_tags!r}")
                seq = ruamel.yaml.comments.CommentedSeq(new_tags)
                seq.fa.set_flow_style()
                role_entry["tags"] = seq
                modified = True

    if modified and not dry_run:
        with open(path, "w") as f:
            yaml.dump(data, f)

    return modified


def main():
    dry_run = "--dry-run" in sys.argv
    playbooks = sorted(PLAYBOOKS_DIR.rglob("*.yaml"))
    changed = []

    for path in playbooks:
        if dry_run:
            modified = False
            yaml = ruamel.yaml.YAML()
            yaml.preserve_quotes = True
            with open(path) as f:
                data = yaml.load(f)
            if isinstance(data, list):
                for play in data:
                    if not isinstance(play, dict) or "roles" not in play:
                        continue
                    for role_entry in play.get("roles", []):
                        if not isinstance(role_entry, dict):
                            continue
                        role_name = role_entry.get("role")
                        if not role_name or is_galaxy_role(role_name):
                            continue
                        current_tags = role_entry.get("tags")
                        new_tags = fix_tags(current_tags, role_name)
                        if new_tags != (list(current_tags) if current_tags else []):
                            if not modified:
                                print(f"\n{path.relative_to(PLAYBOOKS_DIR.parent)}")
                                modified = True
                            print(f"  {role_name}: {list(current_tags) if current_tags else []} -> {new_tags}")
            if modified:
                changed.append(path)
        else:
            if process_file(path, dry_run=False):
                changed.append(path)
                print(f"Updated: {path.relative_to(PLAYBOOKS_DIR.parent)}")

    print(f"\n{'Would update' if dry_run else 'Updated'} {len(changed)} file(s).")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x scripts/fix-playbook-tags.py
```

---

## Task 2: Dry run — review changes before applying

**Files:**
- Read output of dry run

- [ ] **Step 1: Run in dry-run mode**

```bash
cd /Users/charlie/Code/awfulwoman/infra && python3 scripts/fix-playbook-tags.py --dry-run
```

Expected: a list of all role entries that will be changed, showing before → after tags.

- [ ] **Step 2: Verify output looks correct**

Check that:
- Galaxy roles (`infothrill.nullmailer`, `xanmanning.k3s`, `weareinteractive.environment`) are NOT listed
- All `compositions` entries show change to `composition`
- The typo `composition-container-managements` is corrected
- Roles with no tags now get both type and role-name tags
- Roles that already have correct tags (like `system-emailbackup` with `[system, system-emailbackup]`) are NOT listed

---

## Task 3: Apply changes

- [ ] **Step 1: Run the script**

```bash
cd /Users/charlie/Code/awfulwoman/infra && python3 scripts/fix-playbook-tags.py
```

Expected output: a list of ~35-40 updated files ending with `Updated N file(s).`

- [ ] **Step 2: Check git diff looks right**

```bash
git diff playbooks/ | head -100
```

Expected: only `tags:` lines changed — no structural changes to plays, handlers, or non-role sections.

---

## Task 4: Verify correctness

- [ ] **Step 1: Verify no role is missing its type or name tag**

```bash
python3 - <<'EOF'
import ruamel.yaml
from pathlib import Path

PLAYBOOKS_DIR = Path("playbooks")
errors = []

for path in sorted(PLAYBOOKS_DIR.rglob("*.yaml")):
    yaml = ruamel.yaml.YAML()
    with open(path) as f:
        data = yaml.load(f)
    if not isinstance(data, list):
        continue
    for play in data:
        if not isinstance(play, dict) or "roles" not in play:
            continue
        for role_entry in play.get("roles", []):
            if not isinstance(role_entry, dict):
                continue
            role_name = role_entry.get("role")
            if not role_name or "." in role_name:
                continue
            tags = list(role_entry.get("tags") or [])
            type_tag = role_name.split("-")[0]
            if type_tag not in tags:
                errors.append(f"{path}: {role_name} missing type tag '{type_tag}' (has {tags})")
            if role_name not in tags:
                errors.append(f"{path}: {role_name} missing role name tag (has {tags})")
            if "compositions" in tags:
                errors.append(f"{path}: {role_name} still has 'compositions' (should be 'composition')")

if errors:
    print(f"ERRORS ({len(errors)}):")
    for e in errors:
        print(f"  {e}")
else:
    print("All custom roles have correct tags.")
EOF
```

Expected: `All custom roles have correct tags.`

- [ ] **Step 2: Validate playbooks still parse correctly**

```bash
ansible-playbook --syntax-check playbooks/hosts/server-64gb-storage/core.yaml 2>&1 | tail -5
ansible-playbook --syntax-check playbooks/hosts/minipc-8gb-homebrain/core.yaml 2>&1 | tail -5
ansible-playbook --syntax-check playbooks/groups/zfs_backup_servers/core.yaml 2>&1 | tail -5
```

Expected: `playbook: playbooks/hosts/.../core.yaml` with no errors.

---

## Task 5: Commit

- [ ] **Step 1: Stage changes**

```bash
git add playbooks/ scripts/fix-playbook-tags.py
```

- [ ] **Step 2: Run pre-commit**

```bash
pre-commit run --files $(git diff --cached --name-only | tr '\n' ' ')
```

Fix any issues before committing.

- [ ] **Step 3: Commit**

```bash
git commit -m "$(cat <<'EOF'
feat: ensure all playbook roles have type and role-name tags

Every custom role now has a type tag matching its prefix (e.g.
`composition` for `composition-*`) and an exact role-name tag,
enabling targeted runs like `--tags composition-homeassistant`.

Also fixes `compositions` → `composition` throughout and corrects
the `composition-container-managements` typo.
EOF
)"
```
