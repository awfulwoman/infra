#!/bin/bash
BOOTSTRAP_USER_ID=$(id -un)
BOOTSTRAP_GROUP_ID=$(id -gn)
ANSIBLEPULL_REPO_URL=https://github.com/awfulwoman/infra.git
ANSIBLE_VAULT_PASSWORD=""


read -sp "Playbook to use: " ANSIBLEPULL_PLAYBOOK

# Check for defined paths

if [[ -z "${HOME_REPO_DIR}" ]]; then
#   HOME_REPO_DIR="$ANSIBLE_PATH/home"
  HOME_REPO_DIR="/opt/home.git"
fi

if [[ -z "${ANSIBLE_PATH}" ]]; then
  ANSIBLE_PATH="/opt/ansible"
fi

if [[ -z "${ANSIBLE_COLLECTIONS_PATH}" ]]; then
    ANSIBLE_COLLECTIONS_PATH="$ANSIBLE_PATH/collections"
fi
if [[ -z "${ANSIBLE_ROLES_PATH}" ]]; then
    ANSIBLE_ROLES_PATH="$HOME_REPO_DIR/ansible/roles;$ANSIBLE_PATH/galaxy-roles"
fi

ANSIBLE_VAULT_PASSWORD_FILE=$ANSIBLE_PATH/.vaultpassword

echo "DEBUG VARS"
echo "-----------"
echo "ANSIBLE_PATH = $ANSIBLE_PATH"
echo "BOOTSTRAP_USER_ID = $BOOTSTRAP_USER_ID"
echo "BOOTSTRAP_GROUP_ID = $BOOTSTRAP_GROUP_ID"
echo "ANSIBLEPULL_REPO_URL = $ANSIBLEPULL_REPO_URL"
echo "ANSIBLE_VAULT_PASSWORD = $ANSIBLE_VAULT_PASSWORD"
echo "ANSIBLE_COLLECTIONS_PATH = $ANSIBLE_COLLECTIONS_PATH"
echo "ANSIBLE_ROLES_PATH = $ANSIBLE_ROLES_PATH"
echo "HOME_REPO_DIR = $HOME_REPO_DIR"
echo "ANSIBLE_VAULT_PASSWORD_FILE = $ANSIBLE_VAULT_PASSWORD_FILE"

# Import keys
ssh-import-id-gh awfulwoman

# Install Ansible
which ansible
if [[ $? != 0 ]] ; then
    sudo apt update
    sudo apt install software-properties-common -y
    sudo add-apt-repository --yes --update ppa:ansible/ansible
    sudo apt install ansible -y
fi

# Ensure repo location exists
echo " "
echo "UPDATE LOCAL REPO"
echo "************************************"
if [ ! -d "$HOME_REPO_DIR" ]; then
    echo "$HOME_REPO_DIR does not exist. Creating."
    sudo mkdir -p $HOME_REPO_DIR
    sudo chown -R $BOOTSTRAP_USER_ID:$BOOTSTRAP_GROUP_ID $HOME_REPO_DIR
else
    echo "$HOME_REPO_DIR exists. Destroying and recreating."
		sudo rm -rf $HOME_REPO_DIR
		sudo mkdir -p $HOME_REPO_DIR
    sudo chown -R $BOOTSTRAP_USER_ID:$BOOTSTRAP_GROUP_ID $HOME_REPO_DIR
		git clone $ANSIBLEPULL_REPO_URL $HOME_REPO_DIR
fi

# Ensure ansible vault password is present
echo " "
echo "ENSURE ANSIBLE PASSWORD FILE EXISTS"
echo "************************************"
if [ ! -f "$ANSIBLE_PATH/.vaultpassword" ]; then
	if [[ -z "${ANSIBLE_VAULT_PASSWORD}" ]]; then
  	    read -sp "Vault password: " ANSIBLE_VAULT_PASSWORD
				sudo chown -R $BOOTSTRAP_USER_ID:$BOOTSTRAP_GROUP_ID $ANSIBLE_PATH
				echo $ANSIBLE_VAULT_PASSWORD > $ANSIBLE_PATH/.vaultpassword
        echo "Password file created."
	fi
  if [[ $(< $ANSIBLE_PATH/.vaultpassword) != "$ANSIBLE_VAULT_PASSWORD" ]]; then
		sudo chown -R $BOOTSTRAP_USER_ID:$BOOTSTRAP_GROUP_ID $ANSIBLE_PATH
    echo $ANSIBLE_VAULT_PASSWORD > $ANSIBLE_PATH/.vaultpassword
    echo "Password file updated."
  fi
else
	echo "Password file already exists."
fi



cd $HOME_REPO_DIR

# Satisfy Ansible role dependencies
echo " "
echo "UPDATE ANSIBLE GALAXY ROLES"
echo "************************************"
sudo mkdir -p $ANSIBLE_ROLES_PATH
sudo chown -R awful:awful $ANSIBLE_ROLES_PATH
ansible-galaxy install -r $HOME_REPO_DIR/ansible/meta/requirements.yaml -p $ANSIBLE_ROLES_PATH

echo " "
echo "UPDATE ANSIBLE GALAXY COLLECTIONS"
echo "************************************"
sudo mkdir -p $ANSIBLE_COLLECTIONS_PATH
sudo chown -R awful:awful $ANSIBLE_COLLECTIONS_PATH
ansible-galaxy collection install -r $HOME_REPO_DIR/ansible/meta/requirements.yaml -p $ANSIBLE_COLLECTIONS_PATH


# Run Ansible Pull
ansible-pull -U $ANSIBLEPULL_REPO_URL "ansible/playbooks/$ANSIBLEPULL_PLAYBOOK.yaml" --vault-password-file $ANSIBLE_VAULT_PASSWORD_FILE
