# Virtual QEMU Guest

Installs `qemu-guest-agent` on a VM running as a QEMU/KVM guest.

The guest agent runs inside the VM and enables the hypervisor host to query guest state (IP addresses, OS info, filesystem freeze for consistent snapshots) and send commands (graceful shutdown, file injection) via the QEMU guest agent protocol. A reboot is triggered after installation since the agent requires kernel module initialisation.

## Design Notes

- No variables. The role is intentionally minimal — just the agent package and a reboot notification.
- The reboot handler is notified on package install, so it only triggers when the agent is first installed, not on subsequent runs.
- Apply this role to all VMs managed by a `virtual-qemu-host` host.
