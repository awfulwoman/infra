#!/bin/bash
# Run all host core playbooks in sequence, updating Galaxy dependencies first

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

ansible-galaxy collection install -r meta/requirements.yaml --upgrade

find playbooks/hosts -name "core.yaml" | sort | while read -r playbook; do
    echo "==> Running $playbook"
    ansible-playbook "$playbook"
done
