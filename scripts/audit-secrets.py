#!/usr/bin/env python3
"""Audit the 1Password Infra vault against the naming scheme and this repo.

Prints names only, never values. Exit 1 if there are errors; warnings alone
exit 0. Reads OP_CONNECT_HOST, OP_CONNECT_TOKEN and OP_CONNECT_VAULT from the
environment (the audit-secrets playbook sets them from Ansible variables).
"""

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "plugins" / "lookup"))

from op_audit import audit, find_references  # noqa: E402
from op_connect_client import OpConnectClient, OpConnectError  # noqa: E402

SCAN_DIRS = ["roles", "playbooks", "inventory", "scripts"]
SKIP_NAMES = {"audit-secrets.py", "audit-secrets.yaml"}


def repo_files():
    for directory in SCAN_DIRS:
        for path in (REPO / directory).rglob("*"):
            if not path.is_file() or path.name in SKIP_NAMES or path.name.startswith("vault_"):
                continue
            if "__pycache__" in path.parts or path.suffix in {".pyc", ".png", ".jpg", ".ico"}:
                continue
            yield path


def main():
    try:
        client = OpConnectClient(
            os.environ.get("OP_CONNECT_HOST", ""),
            os.environ.get("OP_CONNECT_TOKEN", ""),
            os.environ.get("OP_CONNECT_VAULT", ""),
        )
        items = client.item_metadata()
    except OpConnectError as err:
        print(f"ERROR: {err}")
        return 2

    refs, corpus = [], []
    for path in repo_files():
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


if __name__ == "__main__":
    sys.exit(main())
