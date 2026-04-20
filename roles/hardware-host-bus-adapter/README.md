# Hardware Host Bus Adapter

Configures a Linux host for PCI passthrough of a host bus adapter (HBA) or other PCIe device to a virtual machine via VFIO. This is the prerequisite setup needed before a QEMU/KVM VM can claim direct ownership of a PCIe device (e.g. an HBA for ZFS direct disk access).

The role makes two changes:

1. **GRUB**: Adds `intel_iommu=on` to `GRUB_CMDLINE_LINUX_DEFAULT` and rebuilds the bootloader config.
2. **Kernel modules**: Ensures `vfio`, `vfio_iommu_type1`, `vfio_pci`, and `vfio_virqfd` are loaded at boot via `/etc/modules`, and rebuilds initramfs.

Both steps are conditional — GRUB and initramfs are only rebuilt when a change was actually made.

## Notes

- A reboot is required after first application for IOMMU and VFIO modules to take effect.
- This role is Intel-specific (`intel_iommu=on`). AMD hosts require `amd_iommu=on` instead.
- The specific PCIe device IDs to bind to VFIO (`vfio-pci.ids=`) are not managed here — that is left to the VM definition or additional host configuration.
