#!/bin/bash
# Restrict SSH commands to only allow ZFS receive operations.
# This script is used as a forced command in authorized_keys to limit
# what the backup server can do on this untrusted archive host.

export PATH=/usr/sbin:/usr/bin:$PATH

# Regex patterns for validation
_RE_DATASET='[a-zA-Z0-9/_-]+'
_RE_SNAPSHOT='[a-zA-Z0-9/_-]+@[a-zA-Z0-9/_:-]+'

_WHITELIST=(
    # Connectivity check
    -e "^ls$"
    # List datasets (for checking existence)
    -e "^zfs list ${_RE_DATASET}$"
    # List snapshots (for incremental sync detection)
    -e "^zfs list -t snapshot -H -o name -s creation -r ${_RE_DATASET}$"
    # Create parent datasets one level at a time (unmounted, since we don't need to access data here)
    -e "^zfs create -o canmount=off ${_RE_DATASET}$"
    # Receive backup streams unmounted (the main operation)
    -e "^zfs receive -F -u ${_RE_DATASET}$"
)

# Check if command matches whitelist
if echo "$SSH_ORIGINAL_COMMAND" | grep -qE "${_WHITELIST[@]}"; then
    # Execute command with stdin preserved (critical for zfs receive)
    exec bash -c "$SSH_ORIGINAL_COMMAND"
else
    logger -p local0.crit "BLOCKED non-whitelisted command (client $SSH_CLIENT): $SSH_ORIGINAL_COMMAND"
    echo "Command not permitted" >&2
    exit 1
fi
