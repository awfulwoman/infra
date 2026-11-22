variable "libvirt_uri" {
  type        = string
  description = "libvirt connection URI. The default is the local daemon's unix socket."
  default     = "qemu:///system"
}

variable "bridge_interface" {
  type        = string
  description = "Host interface a VM on the home network is bridged onto."
  default     = "enp3s0"
}
