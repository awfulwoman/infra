#!/bin/bash
# Run all core playbooks, updating Galaxy dependencies first

set -e

ansible-galaxy collection install -r meta/requirements.yaml --upgrade
ansible-playbook playbooks/core.yaml
