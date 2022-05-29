terraform {
  required_providers {
    digitalocean = {
      source = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
    libvirt = {
      source = "dmacvicar/libvirt"
      version = "0.6.14"
    }
  }
}