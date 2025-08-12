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
git -C {{ ansiblepull_workdir }}/home/ pull

# echo " "
# echo "UPDATE ANSIBLE GALAXY ROLES"
# echo "************************************"
# ansible-galaxy install -r {{ ansiblepull_workdir }}/{{ repo_name }}/ansible/meta/requirements.yaml -p {{ ansiblepull_workdir }}/galaxy-roles

# echo " "
# echo "UPDATE ANSIBLE GALAXY COLLECTIONS"
# echo "************************************"
# ansible-galaxy collection install -r {{ ansiblepull_workdir }}/{{ repo_name }}/ansible/meta/requirements.yaml -p {{ ansiblepull_workdir }}/collections

echo " "
echo "RUN ANSIBLE PLAYBOOKS"
echo "************************************"
ansible-pull -U {{ ansiblepull_repo_url }} ansible/playbooks/{{ host_type }}/{{ ansiblepull_playbook }}.yaml

if [ $? -eq 0 ]
then
  echo "ansible-pull-full success"
	# Tell healthchecks.io that all is okay
  /usr/bin/curl -fsSL https://hc-ping.com/{{ vault_autorestic_ping_key }}/{{ inventory_hostname }}-ansible-pull-full > /dev/null
else
  echo "ansible-pull-full failure"
	# Report error via Pushover
	# /usr/bin/curl -s --form-string token="{{ vault_pushover_home_automation_key }}" --form-string user="{{ vault_pushover_user_key }}" --form-string message="{{ inventory_hostname }} ansible-pull failed - $(date --iso-8601=seconds)" https://api.pushover.net/1/messages.json > /dev/null
fi
