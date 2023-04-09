#!/bin/bash

if [[ -z "${ANSIBLE_PATH}" ]]; then
  ANSIBLE_PATH="/opt/ansible"
fi

if [[ -z "${HOME_REPO_DIR}" ]]; then
  HOME_REPO_DIR="$ANSIBLE_PATH/home"
  # HOME_REPO_DIR="/opt/home"
fi


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
git -C "$HOME_REPO_DIR" pull

echo " "
echo "UPDATE ANSIBLE GALAXY ROLES"
echo "************************************"
ansible-galaxy install -r $HOME_REPO_DIR/ansible/meta/requirements.yaml -p $ANSIBLE_PATH/galaxy-roles

echo " "
echo "UPDATE ANSIBLE GALAXY COLLECTIONS"
echo "************************************"
ansible-galaxy collection install -r $HOME_REPO_DIR/ansible/meta/requirements.yaml -p $ANSIBLE_PATH/collections
