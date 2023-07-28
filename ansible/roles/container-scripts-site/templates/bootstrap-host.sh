#!/bin/bash

# Base info
BOOTSTRAP_USER_ID=$(id -un)
BOOTSTRAP_GROUP_ID=$(id -gn)
ANSIBLEPULL_REPO_URL="{{ repo_url }}"
ANSIBLE_VAULT_PASSWORD="{{ vault_ansible_password }}"


# Check for defined paths
if [[ -z "${ANSIBLE_PATH}" ]]; then
  export ANSIBLE_PATH="/opt/ansible"
fi

if [[ -z "${HOME_REPO_DIR}" ]]; then
#   HOME_REPO_DIR="$ANSIBLE_PATH/home"
  HOME_REPO_DIR="/opt/home.git"
fi

export ANSIBLE_VAULT_PASSWORD_FILE="${ANSIBLE_PATH}/.vaultpassword"

if [[ -z "${ANSIBLE_COLLECTIONS_PATH}" ]]; then
    export ANSIBLE_COLLECTIONS_PATH="$ANSIBLE_PATH/collections"
fi
if [[ -z "${ANSIBLE_ROLES_PATH}" ]]; then
    export ANSIBLE_ROLES_PATH="$ANSIBLE_PATH/galaxy-roles:$HOME_REPO_DIR/ansible/roles"
fi
if [[ -z "${ANSIBLE_ROLES_PATH}" ]]; then
    export ANSIBLE_ROLES_PATH="$ANSIBLE_PATH/galaxy-roles:$HOME_REPO_DIR/ansible/roles"
fi
if [[ -z "${ANSIBLE_PLAYBOOK_DIR}" ]]; then
    export ANSIBLE_PLAYBOOK_DIR="$HOME_REPO_DIR/ansible/playbooks"
fi

# DEBUG
echo " "
echo "DEBUG INFO"
echo "************************************"
echo "HOME_REPO_DIR: $HOME_REPO_DIR"
echo "ANSIBLE_PATH: $ANSIBLE_PATH"
echo "ANSIBLE_VAULT_PASSWORD_FILE: $ANSIBLE_VAULT_PASSWORD_FILE"
echo "ANSIBLE_COLLECTIONS_PATH: $ANSIBLE_COLLECTIONS_PATH"
echo "ANSIBLE_ROLES_PATH: $ANSIBLE_ROLES_PATH"
echo "ANSIBLEPULL_REPO_URL: $ANSIBLEPULL_REPO_URL"
echo "BOOTSTRAP_USER_ID: $BOOTSTRAP_USER_ID"
echo "BOOTSTRAP_GROUP_ID: $BOOTSTRAP_GROUP_ID"

# Import keys
echo " "
echo "IMPORT PUBLIC KEYS"
echo "************************************"
ssh-import-id-gh whalecoiner

echo " "
echo "UPDATE APT"
echo "************************************"
sudo apt -q update 

which pip3
if [[ $? != 0 ]] ; then
echo " "
echo "INSTALLING PIP"
echo "************************************"
sudo apt install python3-pip -y
fi

# Install Ansible
which ansible
if [[ $? != 0 ]] ; then
echo " "
echo "INSTALLING ANSIBLE VIA PIP"
echo "************************************"
sudo pip3 install ansible
fi

# Ensure repo location exists
echo " "
echo "BUILD & UPDATE LOCAL REPO"
echo "************************************"
if [ ! -d "$HOME_REPO_DIR" ]; then
    echo "$HOME_REPO_DIR does not exist. Creating."
    sudo mkdir -p $HOME_REPO_DIR
    sudo chown -R $BOOTSTRAP_USER_ID:$BOOTSTRAP_GROUP_ID $HOME_REPO_DIR
fi

if [ -d "$HOME_REPO_DIR" ]; then
	if [ "$(ls -A $HOME_REPO_DIR)" ]; then
        echo "$HOME_REPO_DIR is not empty. Stupidly assuming it's got a repo in it and pulling."
        git -C "$HOME_REPO_DIR" pull --quiet
	else
        echo "$HOME_REPO_DIR is empty. Cloning repo."
        git clone $ANSIBLEPULL_REPO_URL $HOME_REPO_DIR --quiet
	fi
else
	echo "ERROR: Uh oh. $HOME_REPO_DIR could not be found."
    exit 1
fi

if [ ! -d "$ANSIBLE_PATH" ]; then
echo " "
echo "ENSURE ANSIBLE PATH EXISTS"
echo "************************************"
echo "Creating $ANSIBLE_PATH"
sudo mkdir -p $ANSIBLE_PATH
sudo chown -R $BOOTSTRAP_USER_ID:$BOOTSTRAP_GROUP_ID $ANSIBLE_PATH
fi

if [ ! -f "$ANSIBLE_VAULT_PASSWORD_FILE" ]; then
echo " "
echo "ENSURE ANSIBLE PASSWORD FILE EXISTS"
echo "************************************"
echo "Creating $ANSIBLE_VAULT_PASSWORD_FILE"
echo $ANSIBLE_VAULT_PASSWORD > $ANSIBLE_VAULT_PASSWORD_FILE
fi

# Satisfy Ansible role dependencies
echo " "
echo "UPDATE ANSIBLE GALAXY ROLES"
echo "************************************"
if [ ! -d "$ANSIBLE_ROLES_PATH" ]; then
    sudo mkdir -p $ANSIBLE_ROLES_PATH
    sudo chown -R $BOOTSTRAP_USER_ID:$BOOTSTRAP_GROUP_ID $ANSIBLE_ROLES_PATH
fi
ansible-galaxy install -r "$HOME_REPO_DIR/ansible/meta/requirements.yaml" -p $ANSIBLE_ROLES_PATH

echo " "
echo "UPDATE ANSIBLE GALAXY COLLECTIONS"
echo "************************************"
if [ ! -d "$ANSIBLE_COLLECTIONS_PATH" ]; then
    sudo mkdir -p $ANSIBLE_COLLECTIONS_PATH
    sudo chown -R $BOOTSTRAP_USER_ID:$BOOTSTRAP_GROUP_ID $ANSIBLE_COLLECTIONS_PATH
fi
ansible-galaxy collection install -r "$HOME_REPO_DIR/ansible/meta/requirements.yaml" -p $ANSIBLE_COLLECTIONS_PATH

# Run Ansible Pull
echo " "
echo "START ANSIBLE PULL"
echo "************************************"
ansible-pull -U $ANSIBLEPULL_REPO_URL -i "$HOME_REPO_DIR/ansible/inventory/host_vars/{{ item }}.yaml" "$HOME_REPO_DIR/ansible/playbooks/{{ item }}.yaml" --vault-password-file $ANSIBLE_VAULT_PASSWORD_FILE