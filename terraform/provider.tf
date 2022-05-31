terraform {
  required_providers {
    libvirt = {
      source  = "dmacvicar/libvirt"
      version = "~> 1.0"
    }
  }
}

provider "libvirt" {
   uri = "qemu+ssh://ubuntu@192.168.1.116/system"
}