variable "hypervisor_uri" {
  type        = string
  description = "Libvirt connection URI (qemu+ssh://user@host/system for remote)"
}

variable "bridge_interface" {
  type        = string
  description = "Bridge interface name for VM networking on hypervisor"
}
