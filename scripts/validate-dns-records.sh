#!/bin/bash
# Fail fast on a duplicate DNS label across hosts, before any deploy touches
# the zone. Runs entirely on localhost — no SSH to any managed host.

set -e

# Ansible refuses to run under a non-UTF-8 locale. git strips most of the
# environment when it invokes a hook, so LANG alone is not enough: if LC_ALL is
# unset, Python can fall back to ISO8859-1 and the pre-commit run fails with
# "Ansible requires the locale encoding to be UTF-8" even though the shell that
# started the commit is UTF-8. Pin it here so the hook does not depend on the
# caller's environment.
export LC_ALL="${LC_ALL:-C.UTF-8}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

trap 'rm -f scripts/dns-records-input.json' EXIT

ansible-playbook playbooks/utility/export-dns-records-input.yaml >/dev/null
python3 scripts/validate-dns-records.py
