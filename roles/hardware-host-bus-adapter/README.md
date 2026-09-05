# Hardware Host Bus Adapter

This role configures a Linux host for PCI passthrough. It prepares a host bus adapter (HBA) or other PCIe device for a virtual machine, through VFIO. This is the setup that a QEMU/KVM VM needs before it can claim direct ownership of a PCIe device. One example is an HBA for direct ZFS disk access.

The role makes two changes:

1. **GRUB**: Adds `intel_iommu=on` to `GRUB_CMDLINE_LINUX_DEFAULT` and rebuilds the bootloader config.
2. **Kernel modules**: Loads `vfio`, `vfio_iommu_type1`, `vfio_pci`, and `vfio_virqfd` at boot, through `/etc/modules`, and rebuilds initramfs.

Both steps are conditional. The role rebuilds GRUB and initramfs only after an actual change.

## Notes

- After the first run, you must reboot the host for the IOMMU and VFIO modules to take effect.
- This role is Intel-specific (`intel_iommu=on`). AMD hosts need `amd_iommu=on` instead.
- This role does not manage the specific PCIe device IDs that bind to VFIO (`vfio-pci.ids=`). Set these in the VM definition or in additional host configuration.
