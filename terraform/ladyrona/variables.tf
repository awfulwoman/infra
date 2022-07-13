variable "network_name" {
  type    = string
  description = "Name of the libvirt network to be created."
  default = "rhce_lab_network"
}

variable "network_cidr" {
  type    = list(string)
  description = "IP address space cidr for the libvirt (nat) network."
  default = ["192.168.100.0/24"]
}

variable "domain_name" {
  type    = string
  description = "Network domain name for guests attached to the network."
  default = "rhce.lab"
}

variable "pool_name" {
  type    = string
  description = "Name of the libvirt (dir) storage pool that will be created."
  default = "kubernetes"
}

variable "username" {
  type    = string
  description = "username for the guests."
  default = "student"
}

variable "ssh_key" {
  type    = string
  description = "ssh key for the admin user."
  default = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOQ29UlI3w1tETIir13UcRaTGsgcsf3MExWFiQCycoBk whalecoiner@mba2011"
}

variable "clientVM_name" {
  type    = string
  description = "Name of the Guest VM that will be created."
  default = "client"
}

variable "clientVM_source_image" {
  type    = string
  description = "Image source for the Guest VM that will be created."
  default = "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64-disk-kvm.img"
  # default = "https://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2"
  # TODO: Update to CentOS 8 when a non versoined cloud image is avaliable: https://wiki.centos.org/Download#Cloud_.2F_Containers
}

variable "clientVM_ram" {
  type    = number
  description = "Guest VM's RAM in MB."
  default = 2048
}

variable "clientVM_vcpus" {
  type    = number
  description = "Guest VM's vCPU count in cores."
  default =  2
}

# Notes: 
#   Needs to be within the `network_cidr` address space. 
#   Can't be the gateway (normally .1) or the broadcast (normally .254) address in a /24 space.
variable "clientVM_ip" {
  type    = list(string)
  description = "List of IP's to assign to the Guest VM."
  default = ["192.168.100.1"]
}

variable "serverVM_name" {
  type    = string
  description = "Name of the Guest VM that will be created."
  default = "server"
}

variable "serverVM_source_image" {
  type    = string
  description = "Image source for the Guest VM that will be created."
  default = "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64-disk-kvm.img"
  # default = "https://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2"
  # TODO: Update to CentOS 8 when a non versoined cloud image is avaliable: https://wiki.centos.org/Download#Cloud_.2F_Containers
}

variable "serverVM_ram" {
  type    = number
  description = "Guest VM's RAM in MB."
  default = 4096
}

variable "serverVM_vcpus" {
  type    = number
  description = "Guest VM's vCPU count in cores."
  default =  4
}

# Notes: 
#   Needs to be within the `network_cidr` address space. 
#   Can't be the gateway (normally .1) or the boradcast (normally .254) address in a /24 space.
variable "serverVM_ip" {
  type    = list(string)
  description = "List of IP's to assign to the Guest VM."
  default = ["192.168.100.10"]
}
 
variable "serverVM_storage_volume_size" {
  type    = number
  description = "The Guest VM will be provided additional storage (in bytes), so data is not saved to the base disk."
  default =  21474836480
}

variable "serverVM_storage_volume_count" {
  type    = number
  description = "Number of additional disks to present to the Guest VM."
  default = 2
}