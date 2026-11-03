terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.60" # Storage Boxes left experimental in 1.60
    }
  }
}
