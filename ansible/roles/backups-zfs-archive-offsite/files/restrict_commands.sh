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
    # Create parent datasets
    -e "^zfs create -p ${_RE_DATASET}$"
    # Receive backup streams (the main operation)
    -e "^zfs receive -F ${_RE_DATASET}$"
)

# Log non-whitelisted commands as security events, execute whitelisted ones
echo "$SSH_ORIGINAL_COMMAND" | \
tee >(grep -Ev "${_WHITELIST[@]}" \
    | while read -r cmd; do logger -p local0.crit "BLOCKED non-whitelisted command (client $SSH_CLIENT): $cmd"; done \
) | \
grep -E "${_WHITELIST[@]}" | bash
