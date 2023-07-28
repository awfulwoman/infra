#!/bin/bash
BOOTSTRAP_USER_ID=$(id -un)
BOOTSTRAP_GROUP_ID=$(id -gn)
ANSIBLEPULL_REPO_URL="{{ repo_url }}"
ANSIBLE_VAULT_PASSWORD="{{ vault_ansible_password }}"


# Check for defined paths
if [[ -z "${ANSIBLE_PATH}" ]]; then
  ANSIBLE_PATH="/opt/ansible"
fi

ANSIBLE_VAULT_PASSWORD_FILE="${ANSIBLE_PATH}/.vaultpassword"

echo $ANSIBLE_VAULT_PASSWORD_FILE

if [[ -z "${ANSIBLE_COLLECTIONS_PATH}" ]]; then
    ANSIBLE_COLLECTIONS_PATH="$ANSIBLE_PATH/collections"
fi
if [[ -z "${ANSIBLE_ROLES_PATH}" ]]; then
    ANSIBLE_ROLES_PATH="$ANSIBLE_PATH/galaxy-roles"
fi

if [[ -z "${HOME_REPO_DIR}" ]]; then
#   HOME_REPO_DIR="$ANSIBLE_PATH/home"
  HOME_REPO_DIR="/opt/home.git"
fi

# Import keys
ssh-import-id-gh whalecoiner

# Install PIP
sudo apt update

which pip3
if [[ $? != 0 ]] ; then
    sudo apt install python3-pip -y
fi

# Install Ansible
which ansible
if [[ $? != 0 ]] ; then
  echo " "
  echo "INSTALL ANSIBLE"
  echo "************************************"
  sudo pip3 install ansible
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
    echo "$HOME_REPO_DIR exists."
fi

# If home repo is empty...
find "$HOME_REPO_DIR" -maxdepth 0 -empty -exec echo {} is empty. \;
# Clone repo
if [[ $? == 0 ]]; then
    echo "No repo present in $HOME_REPO_DIR. Cloning."
    git clone $ANSIBLEPULL_REPO_URL $HOME_REPO_DIR
else
# Update repo
    echo "Update repo."
    git -C "$HOME_REPO_DIR" pull
fi

echo " "
echo "ENSURE ANSIBLE PATH EXISTS"
echo "************************************"
sudo mkdir -p $ANSIBLE_PATH
sudo chown -R ubuntu:ubuntu $ANSIBLE_PATH

echo " "
echo "ENSURE ANSIBLE PASSWORD FILE EXISTS"
echo "************************************"
echo $ANSIBLE_VAULT_PASSWORD > $ANSIBLE_VAULT_PASSWORD_FILE

# Satisfy Ansible role dependencies
echo " "
echo "UPDATE ANSIBLE GALAXY ROLES"
echo "************************************"
cd $HOME_REPO_DIR
sudo mkdir -p $ANSIBLE_ROLES_PATH
sudo chown -R ubuntu:ubuntu $ANSIBLE_ROLES_PATH
ansible-galaxy install -r $HOME_REPO_DIR/ansible/meta/requirements.yaml -p $ANSIBLE_ROLES_PATH

echo " "
echo "UPDATE ANSIBLE GALAXY COLLECTIONS"
echo "************************************"
cd $HOME_REPO_DIR
sudo mkdir -p $ANSIBLE_COLLECTIONS_PATH
sudo chown -R ubuntu:ubuntu $ANSIBLE_COLLECTIONS_PATH
ansible-galaxy collection install -r $HOME_REPO_DIR/ansible/meta/requirements.yaml -p $ANSIBLE_COLLECTIONS_PATH

# Run Ansible Pull
echo " "
echo "START ANSIBLE PULL"
echo "************************************"
cd $HOME_REPO_DIR
ansible-pull -U $ANSIBLEPULL_REPO_URL "ansible/playbooks/{{item}}.yaml" --vault-password-file $ANSIBLE_VAULT_PASSWORD_FILE