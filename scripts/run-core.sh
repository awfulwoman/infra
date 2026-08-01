#!/bin/bash
# Run all host core playbooks in sequence, updating Galaxy dependencies first

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

ansible-galaxy collection install -r meta/requirements.yaml --upgrade

failed=()

while read -r playbook; do
    echo "==> Running $playbook"
    if ! ansible-playbook "$playbook"; then
        failed+=("$playbook")
    fi
done < <(find playbooks/hosts -name "core.yaml" | sort)

if [ "${#failed[@]}" -gt 0 ]; then
    echo "==> Failed playbooks:"
    printf '  %s\n' "${failed[@]}"
    exit 1
fi
