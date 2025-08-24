#!/bin/bash

### Lockfile ###
LOCKFILE="{{ ansiblepull_workdir }}/{{ansiblepull_lockfile_name}}"
LOCKFD=99
_lock()             { flock -$1 $LOCKFD; }
_no_more_locking()  { _lock u; _lock xn && rm -f $LOCKFILE; }
_prepare_locking()  { eval "exec $LOCKFD>\"$LOCKFILE\""; trap _no_more_locking EXIT; }
_prepare_locking
exlock_now()        { _lock xn; }
exlock()            { _lock x; }
shlock()            { _lock s; }
unlock()            { _lock u; }
exlock_now || exit 1

### END Lockfile ###

echo " "
echo "UPDATE GIT"
echo "************************************"
git -C {{ ansiblepull_repo_path }} pull

# echo " "
# echo "UPDATE ANSIBLE GALAXY ROLES"
# echo "************************************"
# ansible-galaxy install -r {{ ansiblepull_repo_path }}/ansible/meta/requirements.yaml -p {{ ansiblepull_workdir }}/galaxy/roles

# echo " "
# echo "UPDATE ANSIBLE GALAXY COLLECTIONS"
# echo "************************************"
# ansible-galaxy collection install -r {{ ansiblepull_repo_path }}/ansible/meta/requirements.yaml -p {{ ansiblepull_workdir }}/galaxy/collections

echo " "
echo "RUN ANSIBLE PLAYBOOKS"
echo "************************************"
ansible-pull --url {{ ansiblepull_repo_url }} --directory {{ ansiblepull_repo_path }} ansible/playbooks/{{ host_type }}/{{ inventory_hostname }}/{{ ansiblepull_playbook }}.yaml
