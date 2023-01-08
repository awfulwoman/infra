#!/bin/bash

# Check is Lock File exists, if not create it and set trap on exit
 if { set -C; 2>/dev/null >~/ansible-pull-full.lock; }; then
         trap "rm -f ~/ansible-pull-full.lock" EXIT
 else
         echo "Cannot get lock as ~/ansible-pull-full.lock exists."
         exit
 fi

TZ=UTC ansible-pull -U https://github.com/whalecoiner/home ansible/playbooks/{{ inventory_hostname }}.yaml

if [ $? -eq 0 ]
then
  echo "ansible-pull success"
  # Ensure that galaxy has been marked as installeda t least once
  touch /opt/ansible/home.git/.installed.lock
  /usr/bin/curl -fsSL https://hc-ping.com/{{ vault_autorestic_ping_key }}/{{ inventory_hostname }}-ansible-pull
else
  echo "ansible-pull failure"
fi
