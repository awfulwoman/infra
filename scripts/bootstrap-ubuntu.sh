#!/bin/bash

# Install Ansible
which ansible
if [[ $? != 0 ]] ; then
  python3 -m pip install ansible
fi

# Satisfy Ansible role dependencies
git -C /opt/ansible/home/ pull
ansible-galaxy install -r /opt/ansible/home/ansible/meta/requirements.yaml -p /opt/ansible/galaxy-roles
ansible-galaxy collection install -r /opt/ansible/home/ansible/meta/requirements.yaml -p /opt/ansible/galaxy-roles
