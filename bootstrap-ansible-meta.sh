#!/bin/bash
# /opt/ansible/home is standard install location on hosts

cd /opt/ansible/home/
git pull
ansible-galaxy install -r /opt/ansible/home/ansible/meta/requirements.yaml -p /opt/ansible/galaxy-roles
ansible-galaxy collection install -r /opt/ansible/home/ansible/meta/requirements.yaml -p /opt/ansible/galaxy-roles
