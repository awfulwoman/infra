variable "workervm_name" {
  type    = string
  description = "Name of the Guest VM that will be created."
  default = "worker"
}

variable "workervm_source_image" {
  type    = string
  description = "Image source for the Guest VM that will be created."
  default = "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64-disk-kvm.img"
  # default = "https://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2"
  # TODO: Update to CentOS 8 when a non versoined cloud image is avaliable: https://wiki.centos.org/Download#Cloud_.2F_Containers
}

variable "workervm_ram" {
  type    = number
  description = "Guest VM's RAM in MB."
  default = 2048
}

variable "workervm_vcpus" {
  type    = number
  description = "Guest VM's vCPU count in cores."
  default =  2
}

# Notes: 
#   Needs to be within the `network_cidr` address space. 
#   Can't be the gateway (normally .1) or the broadcast (normally .254) address in a /24 space.
variable "workervm_ip" {
  type    = list(string)
  description = "List of IP's to assign to the Guest VM."
  default = ["192.168.100.1"]
}
