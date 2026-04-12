variable "hypervisor_uri" {
  type        = string
  description = "Libvirt connection URI (qemu+ssh://user@host/system for remote)"
  default     = "qemu:///system"  # Local libvirt for manual testing
}
