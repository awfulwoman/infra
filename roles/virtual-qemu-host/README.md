# Virtual QEMU Host

Configures an Ubuntu host to run QEMU/KVM virtual machines using libvirt, and optionally provisions VMs via Terraform with the `dmacvicar/libvirt` provider.

The role installs the full libvirt/QEMU stack, adds the Ansible user to the `libvirt` and `kvm` groups, loads the `vhost_net` kernel module for improved network performance, and configures `qemu.conf` to disable the SELinux security driver (appropriate for Ubuntu which uses AppArmor rather than SELinux).

## Terraform Integration

The role includes Terraform templates under `templates/storage/` for provisioning worker and controller VMs via the libvirt provider. These templates define:

- A storage pool backed by a ZFS dataset
- Ubuntu Jammy cloud image volumes as base images
- Per-VM disk volumes cloned from the base image (qcow2 format)
- Cloud-init disks for initial VM configuration
- `libvirt_domain` resources for worker and controller node groups

The Terraform configuration is rendered by Ansible and then applied during the playbook run — Ansible acts as the orchestrator for Terraform rather than running Terraform directly from a workstation.

## Design Notes

- SELinux security driver is disabled (`security_driver = "none"`) because Ubuntu uses AppArmor. Without this, libvirt may refuse to start VMs.
- `qemu.conf` is configured to run QEMU processes as `ansible_user` rather than the default `libvirt-qemu` user, simplifying file permission management for VM images stored on ZFS datasets.
- The `vhost_net` module enables kernel-bypass networking for VMs, reducing CPU overhead for network-heavy workloads.
- Network definition and virsh commands are present but commented out — idempotent virsh network management is a known rough edge.
- Adding the user to `libvirt`/`kvm` groups triggers a reboot handler since group membership requires a new session to take effect.
