terraform {
  required_providers {
    proxmox = {
      source = "telmate/proxmox"
      version = "2.9.6"
    }
  }
}

provider "proxmox" {
  # Configuration options
}