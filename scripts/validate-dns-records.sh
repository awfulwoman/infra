#!/bin/bash
# Fail fast on a duplicate DNS label across hosts, before any deploy touches
# the zone. Runs entirely on localhost — no SSH to any managed host.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

trap 'rm -f scripts/dns-records-input.json' EXIT

ansible-playbook playbooks/utility/export-dns-records-input.yaml >/dev/null
python3 scripts/validate-dns-records.py
