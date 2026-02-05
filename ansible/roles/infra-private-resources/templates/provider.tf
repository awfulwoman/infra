terraform {
  required_providers {
    libvirt = {
      source  = "dmacvicar/libvirt"
      version = "~> 0.9.2"
    }
  }
}

provider "libvirt" {
  uri = "qemu:///system"
}
