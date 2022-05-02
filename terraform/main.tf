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
  pm_api_url = "https://p192.168.1.116:8006/api2/json"
}