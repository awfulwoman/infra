terraform {
  required_providers {
    proxmox = {
      source = "telmate/proxmox"
      version = "2.9.10"
    }
  }
}

provider "proxmox" {
  # Configuration options
  pm_api_url = "https://192.168.1.116:8006/api2/json"
  # Run the following
  # eval $(op signin) 
  # op run --env-file=.env -- terraform apply
}

resource "proxmox_vm_qemu" "resource-name" {
  name        = "created-via-tf"
  target_node = "pve"
  iso         = "ubuntu-22.04-live-server-amd64.iso"

  ### or for a Clone VM operation
  # clone = "template to clone"

  ### or for a PXE boot VM operation
  # pxe = true
  # boot = "net0;scsi0"
  # agent = 0
}