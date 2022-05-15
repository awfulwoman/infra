terraform {
  required_providers {
    libvirt = {
      source = "dmacvicar/libvirt"
      version = "0.6.14"
    }
  }
}

provider "libvirt" {
   uri = "qemu+ssh://ubuntu@192.168.1.116/system"
}

resource "libvirt_domain" "terraform_test" {
  name = "terraform_test"
}