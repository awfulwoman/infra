variable "network_name" {
  type    = string
  description = "Name of the libvirt network to be created."
  default = "kubernetes_network"
}

variable "network_cidr" {
  type    = list(string)
  description = "IP address space cidr for the libvirt (nat) network."
  default = ["192.168.100.0/24"]
}

variable "domain_name" {
  type    = string
  description = "Network domain name for guests attached to the network."
  default = "i.affordablepotatoes.com"
}

variable "pool_name" {
  type    = string
  description = "Name of the libvirt (dir) storage pool that will be created."
  default = "kubernetes"
}

variable "username" {
  type    = string
  description = "Username for the guests."
  default = "ubuntu"
}

variable "ssh_key" {
  type    = string
  description = "SSH key for the admin user."
  default = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKudLqzujFkNDI6cvO/qdCixN5LlV6qeKz8BLyi5MiKQ charlie@workstation-mba2011"
}
