#!/bin/bash
# Restrict SSH access to libvirt commands only
# This script allows only libvirt-related commands via SSH forced command

set -euo pipefail

# Log all access attempts for audit
logger -t libvirt-ssh "Connection from ${SSH_CLIENT:-unknown} - Command: ${SSH_ORIGINAL_COMMAND:-none}"

# If no command specified, deny
if [ -z "${SSH_ORIGINAL_COMMAND:-}" ]; then
    echo "ERROR: Interactive sessions not allowed" >&2
    logger -t libvirt-ssh "DENIED: Interactive session attempt"
    exit 1
fi

# Whitelist of allowed commands for libvirt operations
case "$SSH_ORIGINAL_COMMAND" in
    # Direct virsh commands
    virsh\ *)
        exec $SSH_ORIGINAL_COMMAND
        ;;
    /usr/bin/virsh\ *)
        exec $SSH_ORIGINAL_COMMAND
        ;;

    # Libvirt daemon socket connection (used by terraform provider)
    nc\ -U\ /var/run/libvirt/libvirt-sock)
        exec nc -U /var/run/libvirt/libvirt-sock
        ;;
    socat\ *)
        # Terraform libvirt provider may use socat for socket forwarding
        if echo "$SSH_ORIGINAL_COMMAND" | grep -q "UNIX-CONNECT:/var/run/libvirt/libvirt-sock"; then
            exec $SSH_ORIGINAL_COMMAND
        else
            echo "ERROR: Only libvirt socket connections allowed via socat" >&2
            logger -t libvirt-ssh "DENIED: Unauthorized socat command: $SSH_ORIGINAL_COMMAND"
            exit 1
        fi
        ;;

    # Deny everything else
    *)
        echo "ERROR: Command not allowed: $SSH_ORIGINAL_COMMAND" >&2
        logger -t libvirt-ssh "DENIED: Unauthorized command: $SSH_ORIGINAL_COMMAND"
        exit 1
        ;;
esac
