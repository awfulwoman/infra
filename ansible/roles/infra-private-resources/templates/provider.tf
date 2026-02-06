terraform {
  required_providers {
    libvirt = {
      source  = "dmacvicar/libvirt"
      version = "~> 0.9.2"
    }
  }
}

# Connect to libvirt on host-storage via SSH
# Terraform runs on dns (control plane), manages VMs on host-storage (hypervisor)
provider "libvirt" {
  uri = var.hypervisor_uri
}
