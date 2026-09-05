# Virtual QEMU Host

Configures an Ubuntu host to run QEMU/KVM virtual machines with libvirt. It can also provision VMs with Terraform and the `dmacvicar/libvirt` provider.

The role installs the full libvirt and QEMU stack. It adds the Ansible user to the `libvirt` and `kvm` groups. It loads the `vhost_net` kernel module, for better network performance. It also configures `qemu.conf` to disable the SELinux security driver. This is correct for Ubuntu, which uses AppArmor instead of SELinux.

## Terraform Integration

The role includes Terraform templates under `templates/storage/`, to provision worker and controller VMs with the libvirt provider. These templates define:

- A storage pool backed by a ZFS dataset
- Ubuntu Jammy cloud image volumes as base images
- Per-VM disk volumes cloned from the base image (qcow2 format)
- Cloud-init disks for initial VM configuration
- `libvirt_domain` resources for worker and controller node groups

Ansible renders the Terraform configuration and applies it during the playbook run. Ansible acts as the orchestrator for Terraform. You do not run Terraform directly from a workstation.

## Design Notes

- The role disables the SELinux security driver (`security_driver = "none"`) because Ubuntu uses AppArmor. Without this, libvirt can refuse to start VMs.
- The role configures `qemu.conf` to run QEMU processes as `ansible_user`, instead of the default `libvirt-qemu` user. This simplifies file permission management for VM images stored on ZFS datasets.
- The `vhost_net` module enables kernel-bypass networking for VMs. This reduces CPU overhead for network-heavy workloads.
- The role includes network definition and virsh commands, but comments them out. Idempotent virsh network management is a known rough edge.
- When the role adds the user to the `libvirt` and `kvm` groups, this triggers a reboot handler. Group membership requires a new session to take effect.
