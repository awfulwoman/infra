#!/bin/bash

# Install Ansible
which ansible
if [[ $? != 0 ]] ; then
	echo " "
	echo "INSTALL ANSIBLE"
	echo "************************************"
  python3 -m pip install ansible
fi

# Satisfy Ansible role dependencies
echo " "
echo "UPDATE GIT"
echo "************************************"
git -C /opt/ansible/home/ pull

echo " "
echo "UPDATE ANSIBLE GALAXY ROLES"
echo "************************************"
ansible-galaxy install -r /opt/ansible/home/ansible/meta/requirements.yaml -p /opt/ansible/galaxy-roles

echo " "
echo "UPDATE ANSIBLE GALAXY COLLECTIONS"
echo "************************************"
ansible-galaxy collection install -r /opt/ansible/home/ansible/meta/requirements.yaml -p /opt/ansible/collections
