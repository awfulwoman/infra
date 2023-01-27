terraform {
  cloud {
    organization = "whalecoiner"

    workspaces {
      name = "domains"
    }
  }
}

terraform {
  required_providers {
    digitalocean = {
      source = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

provider "digitalocean" {
  token = var.digitalocean_token
}

data "digitalocean_domain" "affordablepotatoes" {
  name = "affordablepotatoes.com"
}

output "domain_output" {
  value = data.digitalocean_domain.affordablepotatoes.zone_file
}

resource "digitalocean_domain" "homeassistant" {
  name       = "homeassistant.affordablepotatoes.com"
  ip_address = "192.168.1.103"
}

resource "digitalocean_domain" "jellyfin" {
  name       = "jellyfin.affordablepotatoes.com"
  ip_address = "192.168.1.116"
}

resource "digitalocean_droplet" "host_public" {
  image  = "ubuntu-22-10-x64"
  name   = "host-public"
  region = "fra1"
  size   = "s-1vcpu-1gb"
}
