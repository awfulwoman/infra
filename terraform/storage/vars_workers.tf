variable "workervm_prefix" {
  type    = string
  description = "Name of the Guest VM that will be created."
  default = "worker"
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
