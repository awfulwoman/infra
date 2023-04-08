#!/bin/bash
# /opt/ansible/home is standard install location on hosts

git -C /opt/ansible/home/ pull
ansible-galaxy install -r /opt/ansible/home/ansible/meta/requirements.yaml -p /opt/ansible/galaxy-roles
ansible-galaxy collection install -r /opt/ansible/home/ansible/meta/requirements.yaml -p /opt/ansible/galaxy-roles
