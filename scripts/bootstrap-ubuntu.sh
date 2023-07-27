#!/bin/bash
BOOTSTRAP_USER_ID=$(id -un)
BOOTSTRAP_GROUP_ID=$(id -gn)

# Check for defined paths
if [[ -z "${ANSIBLE_PATH}" ]]; then
  ANSIBLE_PATH="/opt/ansible"
fi

if [[ -z "${HOME_REPO_DIR}" ]]; then
  HOME_REPO_DIR="$ANSIBLE_PATH/home"
  # HOME_REPO_DIR="/opt/home"
fi

# Import keys
ssh-import-id-gh whalecoiner

# Install PIP
sudo apt update
sudo apt install python3-pip -y

# Install Ansible
which ansible
if [[ $? != 0 ]] ; then
  echo " "
  echo "INSTALL ANSIBLE"
  echo "************************************"
  pip3 install ansible
fi

# Satisfy Ansible role dependencies
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


find "$HOME_REPO_DIR" -maxdepth 0 -empty -exec echo {} is empty. \;
if [[ $? != 0 ]]; then
    echo "No repo present in $HOME_REPO_DIR. Cloning."
    git clone https://github.com/whalecoiner/home.git $HOME_REPO_DIR
fi

echo "Update repo."
git -C "$HOME_REPO_DIR" pull

# echo " "
# echo "ENSURE ANSIBLE PASSWORD FILE EXISTS"
# echo "************************************"
# if [ ! -f "$ANSIBLE_PATH/.vaultpassword" ]; then
# 	if [[ -z "${ANSIBLE_VAULT_PASSWORD}" ]]; then
#   	read -sp "Vault password: " ANSIBLE_VAULT_PASSWORD
# 	fi
#   if [[ $(< $ANSIBLE_PATH/.vaultpassword) != "$ANSIBLE_VAULT_PASSWORD" ]]; then
#     echo $ANSIBLE_VAULT_PASSWORD > $ANSIBLE_PATH/.vaultpassword
#   fi
# 	echo "File created."
# else
# 	echo "File exists."
# fi

echo " "
echo "UPDATE ANSIBLE GALAXY ROLES"
echo "************************************"
ansible-galaxy install -r $HOME_REPO_DIR/ansible/meta/requirements.yaml -p $ANSIBLE_PATH/galaxy-roles

echo " "
echo "UPDATE ANSIBLE GALAXY COLLECTIONS"
echo "************************************"
ansible-galaxy collection install -r $HOME_REPO_DIR/ansible/meta/requirements.yaml -p $ANSIBLE_PATH/collections
