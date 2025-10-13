#!/usr/bin/env bash

#################################
# Constants / global variables
#################################
LOGLEVEL='INFO'
QUIET=0 # verbose by default
SKIP_ANSIBLE_PULL=0
SKIPAUSE=0

LOGDIR={{zfsbackup_logging_dir}}
LOGFILE={{zfsbackup_logging_successfile}}
FAILURE=0 # default is success
# SEARCHDOMAIN=.{{ domain_name }}
SEARCHDOMAIN=""

#################################
# Functions
#################################

# Logging functions
function log_output {
  if [ $QUIET -eq 0 ]; then
    echo `date "+%Y/%m/%d %H:%M:%S"`" $1"
  fi
  echo `date "+%Y/%m/%d %H:%M:%S"`" $1" >> $LOGDIR/$LOGFILE
}

function log_debug {
  if [[ "$LOGLEVEL" =~ ^(DEBUG)$ ]]; then
    log_output "[DEBUG] $1"
  fi
}

function log_info {
  if [[ "$LOGLEVEL" =~ ^(DEBUG|INFO)$ ]]; then
    log_output "[INFO] $1"
  fi
}

function log_warn {
  if [[ "$LOGLEVEL" =~ ^(DEBUG|INFO|WARN)$ ]]; then
    log_output "[WARN] $1"
  fi
}

function log_error {
  if [[ "$LOGLEVEL" =~ ^(DEBUG|INFO|WARN|ERROR)$ ]]; then
    log_output "[ERROR] $1"
  fi
}

# Help output
function usage {
  echo
  echo "This is a Bash script that pulls ZFS backups from client machines."
  echo "Usage: pull-zfs-backups -l <logfile> -L <loglevel> --quiet"
  echo "Example: pull-zfs-backups -l example.log -L INFO --quiet"
  echo " "
  echo "Options"
  echo "-l | --logfile "
  echo "                   Change logfile name"
  echo " "
  echo "-L | --loglevel"
  echo "                   Change the log level"
  echo "                   DEBUG|INFO|WARN|ERROR"
  echo " "
  echo "-S | --skip-ansible-pull"
  echo "                   Skip pulling and running ansible playbook for this host"
  echo " "
  echo "-Q | --quiet "
  echo "                   Quieten output"
  echo " "
  echo "-p | --skip-pause "
  echo "                   Skip the default pause"
  echo " "
  echo "-h | --help"
  echo "                   This help"s
  echo " "
}

#################################
# Main
#################################

# Get input parameters
while [[ "$1" != "" ]]; do
  case $1 in
    -l | --logfile )        shift
                            LOGFILE=$1
                            ;;
    -L | --loglevel )       shift
                            LOGLEVEL=$1
                            ;;
    -S | --skip-ansible-pull )       shift
                            SKIP_ANSIBLE_PULL=1
                            ;;
    -Q | --quiet )          shift
                            QUIET=1
                            ;;
    -p | --skip-pause )     shift
                            SKIPAUSE=1
                            ;;
    -h | --help )           usage
                            exit
                            ;;
    * )                     usage
                            exit 1
  esac
  shift
done


# PUBLISH ON BACKING_UP TOPIC

echo "ZFS Backups"
echo "***********"
echo " "

# if [ $SKIPAUSE -eq 0 ]; then
# echo "Pausing for 60 seconds."
# echo " "
# pausesecs=$((1 * 60))
# while [ $pausesecs -gt 0 ]; do
#     echo -ne "🕗 $pausesecs\033[0K\r"
#     sleep 1
#     : $((pausesecs--))
# done
# echo " "
# fi

if [[ "$LOGLEVEL" =~ ^(DEBUG)$ ]]; then
  echo "DEBUG INFO"
  echo "***********"
  echo "Logging to: $LOGDIR/$LOGFILE"
  echo "Search domain: $SEARCHDOMAIN"
  echo " "
fi

sleepnow() {
  # Sleep if script is present
  command -v sleepuntil &> /dev/null
  if [ $? -eq 0 ]; 
  then 
    {% if sleepuntil_sleep_time is defined %}
    log_info "Going to sleep in 5 mins. {{ ansible_hostname }} will wake up at {{ sleepuntil_sleep_time }}."
    {% else %}
    log_info "Going to sleep in 5 mins."
    {% endif %}
    secs=$((5 * 60))
    while [ $secs -gt 0 ]; do
        echo -ne "🕗 $secs\033[0K\r"
        sleep 1
        : $((secs--))
    done
    sleep 5
    echo " "
    # log_info "Calling sleepuntil"

    {% if sleepuntil_sleep_time is defined %}
    sleepuntil --time {{ sleepuntil_sleep_time }}
    {% endif %}
  fi 
}

success () {
  log_info "✅✅✅ Backup success!"

  # MQTT announce backup
  mosquitto_pub -h mqtt.{{ domain_name }} -t servers/backup -m Finished
  # sleepnow
}

failure () {
  log_error "❌❌❌ Backup failure!"
  {% if zfsbackup_pushover %}
  /usr/bin/curl -s --form-string token="{{vault_pushover_home_automation_key}}" --form-string user="{{vault_pushover_user_key}}" --form-string message="Backup failed - $(date --iso-8601=seconds)" https://api.pushover.net/1/messages.json
  {% endif %}

  # MQTT announce backup
  mosquitto_pub -h mqtt.{{ domain_name }} -t servers/backup -m Failed
  # sleepnow
}

prepbackup () {
  # TODO: offer option of logging to stdout or file
  mkdir -p $LOGDIR
  touch $LOGDIR/$LOGFILE
}

publish () {
  mosquitto_pub -h mqtt.{{ domain_name }} -t servers/backup -m $1
}

# Prepare for backup
# *******************
prepbackup

# Perform Ansible pull while the machine is awake
# *******************
{% if (zfsbackup_ansiblepull_workdir) and (zfsbackup_ansiblepull_script_name) %}
if [ $SKIP_ANSIBLE_PULL -eq 0 ]; then
  # MQTT announce backup
  mosquitto_pub -h mqtt.{{ domain_name }} -t servers/backup -m "Running Ansible Pull"
  {{ zfsbackup_ansiblepull_workdir }}/{{ zfsbackup_ansiblepull_script_name }}
fi
{% endif %}

# MQTT announce backup
# *******************
mosquitto_pub -h mqtt.{{ domain_name }} -t servers/backup -m "In Progress"

# Loop over clients
# *******************
{% for zfsbackup_client in query('inventory_hostnames', 'zfs-backup-clients')  %}

# log_info "Backing up {{ zfsbackup_client }}."

## Is the client host up?
# log_info "Pinging {{ zfsbackup_client }}$SEARCHDOMAIN..."
ping "{{ zfsbackup_client }}$SEARCHDOMAIN" -c2 > /dev/null 2>&1
if [ $? -eq 0 ]; 
then 
  log_info "{{ zfsbackup_client }} is online. Proceeding."

  # Loop over client datasets
  # **************************
  {% if hostvars[zfsbackup_client]['zfs_backup_datasets'] %}
  {% for zfs_backup_dataset in hostvars[zfsbackup_client]['zfs_backup_datasets'] %}

  log_info "Starting {{zfs_backup_dataset}}..."

  SYNCOID_COMMAND="sudo /usr/sbin/syncoid --no-privilege-elevation --no-sync-snap --quiet --recursive --skip-parent {% if hostvars[zfsbackup_client]['zfs_backup_datasets_exclude'] is defined %}{% for zfs_backup_dataset_to_exclude in hostvars[zfsbackup_client]['zfs_backup_datasets_exclude'] %}--exclude={{zfs_backup_dataset_to_exclude}} {% endfor %}{% endif %} {{ vault_zfsbackups_user }}@{{ zfsbackup_client }}$SEARCHDOMAIN:{{zfs_backup_dataset}} {{ zfsbackup_poolname }}/{{ zfsbackup_client }}/{{zfs_backup_dataset}}"

  # SYNCOID_OUTPUT=$( $SYNCOID_COMMAND 2>&1 )

  # if [ $? -eq 0 ]
  if $SYNCOID_COMMAND; then
    log_info "Success!"
    # mosquitto_pub -h mqtt.{{ domain_name }} -t servers/backup -m "Backup Success"
  else
    FAILURE=1
    log_error "Failure!" 
    # log_error $SYNCOID_OUTPUT
    # mosquitto_pub -h mqtt.{{ domain_name }} -t servers/backup -m "Backup Failure"
  fi

  if [[ "$LOGLEVEL" =~ ^(DEBUG)$ ]]; then
    echo $SYNCOID_COMMAND
    # echo $SYNCOID_OUTPUT
  fi

  {% endfor %} # End dataset loop
  {% endif %}

  log_info "{{ zfsbackup_client }} backup finished."

else 
  log_warn "{{ zfsbackup_client }} was not online."
  failure
fi # End online status check
echo " "
# ------------------------------------------------
{% endfor %} # End client loop

# Notify of outcome
if [ $FAILURE -eq 1 ]
then
  failure
else
  success
fi

# END PUBLISH ON BACKING_UP TOPIC
