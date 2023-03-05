
variable "controllervm_name" {
  type    = string
  description = "Name of the Guest VM that will be created."
  default = "controller"
}

variable "controllervm_source_image" {
  type    = string
  description = "Image source for the Guest VM that will be created."
  default = "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64-disk-kvm.img"
  # default = "https://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2"
  # TODO: Update to CentOS 8 when a non versoined cloud image is avaliable: https://wiki.centos.org/Download#Cloud_.2F_Containers
}

variable "controllervm_ram" {
  type    = number
  description = "Guest VM's RAM in MB."
  default = 4096
}

variable "controllervm_vcpus" {
  type    = number
  description = "Guest VM's vCPU count in cores."
  default =  4
}

# Notes: 
#   Needs to be within the `network_cidr` address space. 
#   Can't be the gateway (normally .1) or the boradcast (normally .254) address in a /24 space.
variable "controllervm_ip" {
  type    = list(string)
  description = "List of IP's to assign to the Guest VM."
  default = ["192.168.100.10"]
}
 
variable "controllervm_storage_volume_size" {
  type    = number
  description = "The Guest VM will be provided additional storage (in bytes), so data is not saved to the base disk."
  default =  21474836480
}

variable "controllervm_storage_volume_count" {
  type    = number
  description = "Number of additional disks to present to the Guest VM."
  default = 2
}
