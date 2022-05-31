terraform {
  required_providers {
    mycloud = {
      source  = "dmacvicar/libvirt"
      version = "~> 1.0"
    }
  }
}

provider "libvirt" {
   uri = "qemu+ssh://ubuntu@192.168.1.116/system"
}