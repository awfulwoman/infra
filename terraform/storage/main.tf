resource "libvirt_network" "network" {
  name = var.network_name
  mode = "nat"
  addresses = var.network_cidr
  domain = var.domain_name
  dns {
    enabled = true
    local_only = true
  }
  dhcp {enabled = true}
}

# This is the same as the following command:
# virsh pool-define-as default --type dir --target /slowpool/pools/<a pool name>
# https://unix.stackexchange.com/questions/216837/virsh-and-creating-storage-pools-what-is-sourcepath
# It creates a directory and assigns it to the libvirt pool named "<a pool name>"
# The following does the same.

resource "libvirt_pool" "pool" {
  name = var.pool_name
  type = "dir"
  path = "/slowpool/pools/${var.pool_name}"
}

# pool-define-as --name default --source-name filepool --type zfs
# It takes a ZFS pool and assigns it in totality to the libvirt pool named "default"
# The Terraform provider does not yet support ZFS pools so this would have to be done manually.

provider "libvirt" {
   uri = "qemu+ssh://ubuntu@host-storage.i.affordablepotatoes.com/system"
}

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
  default = "k8s.i.affordablepotatoes.com"
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
  default = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJcD9D+x3UWpKnl44gPW+NeaCo8Y8vGe59FU0Y1ddNLo ubuntu@host-storage"
}
