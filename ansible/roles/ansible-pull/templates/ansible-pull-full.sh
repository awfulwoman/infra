#!/bin/bash

# Check is Lock File exists, if not create it and set trap on exit
 if { set -C; 2>/dev/null >~/ansible-pull-full.lock; }; then
         trap "rm -f ~/ansible-pull-full.lock" EXIT
 else
         echo "Cannot get lock as ~/ansible-pull-full.lock exists."
         exit
 fi


# download repo

# cd to download


# run ansible-galaxy from within it 
# Only run this if ansible-pull-full-initialised.lock is not present, and
# then weekly after that.

ansible-galaxy install -f -r ansible/roles/requirements.yaml

# run ansible-pull as before

TZ=UTC ansible-pull -U https://github.com/whalecoiner/home ansible/playbooks/{{ inventory_hostname }}.yaml
