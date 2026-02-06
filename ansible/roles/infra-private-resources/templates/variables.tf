variable "hypervisor_uri" {
  type        = string
  description = "Libvirt connection URI (qemu+ssh://user@host/system for remote)"
  default     = "qemu:///system"  # Local libvirt for manual testing
}

variable "bridge_interface" {
  type        = string
  description = "Bridge interface name for VM networking on hypervisor"
  default     = "enp3s0"  # host-storage primary interface
}
