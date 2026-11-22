terraform {
  required_providers {
    libvirt = {
      source  = "dmacvicar/libvirt"
      version = "~> 0.9.2"
    }
  }
}

# The provider's client is pure Go and speaks the libvirt remote protocol over
# the unix socket, so it reaches the daemon on this host directly. No virsh,
# no libvirt-clients, no SSH.
provider "libvirt" {
  uri = var.libvirt_uri
}
