#!/bin/bash
# Fail fast on a composition that never stated a ZFS policy, before a deploy
# leaves it unprotected. Reads the inventory directly: no SSH to any managed
# host, no Ansible run, and no vault password.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# The validator needs PyYAML to read the inventory. A Homebrew python3 does
# not bundle it, but this repo's own Ansible is a hard dependency and its
# bundled interpreter always has it, so fall back to that rather than asking
# for a venv the project otherwise does without.
PY=python3
if ! "$PY" -c 'import yaml' 2>/dev/null; then
  ANSIBLE_BIN="$(command -v ansible || true)"
  if [ -n "$ANSIBLE_BIN" ]; then
    ANSIBLE_PY="$(head -1 "$ANSIBLE_BIN" | sed 's|^#!||')"
    if [ -x "$ANSIBLE_PY" ] && "$ANSIBLE_PY" -c 'import yaml' 2>/dev/null; then
      PY="$ANSIBLE_PY"
    fi
  fi
fi

if ! "$PY" -c 'import yaml' 2>/dev/null; then
  echo "validate-zfs-policies: no Python with PyYAML found" >&2
  echo "  tried python3 and the interpreter behind 'ansible'" >&2
  exit 1
fi

exec "$PY" scripts/validate-zfs-policies.py "$@"
