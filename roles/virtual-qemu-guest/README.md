# Virtual QEMU Guest

Installs `qemu-guest-agent` on a VM that runs as a QEMU/KVM guest.

The guest agent runs inside the VM. It enables the hypervisor host to query guest state, for example IP addresses, OS information, or filesystem freeze for consistent snapshots. It also lets the host send commands, for example graceful shutdown or file injection, with the QEMU guest agent protocol. The role triggers a reboot after installation, because the agent requires kernel module initialization.

## Design Notes

- The role has no variables. It is intentionally minimal: the agent package and a reboot notification.
- The package install step notifies the reboot handler. This means the handler triggers only when the agent is first installed, not on later runs.
- Apply this role to all VMs managed by a `virtual-qemu-host` host.
