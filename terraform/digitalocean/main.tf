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
  ip_address = "100.89.157.31"
}

resource "digitalocean_domain" "homeautomation" {
  name       = "homeautomation.affordablepotatoes.com"
  ip_address = "100.89.157.31"
}

resource "digitalocean_domain" "esphome" {
  name       = "esphome.affordablepotatoes.com"
  ip_address = "100.89.157.31"
}

resource "digitalocean_domain" "zigbee2mqtt" {
  name       = "zigbee2mqtt.affordablepotatoes.com"
  ip_address = "100.89.157.31"
}

resource "digitalocean_domain" "zigbee2mqtt-aqara" {
  name       = "zigbee2mqtt-aqara.affordablepotatoes.com"
  ip_address = "100.89.157.31"
}

resource "digitalocean_domain" "uptimekuma" {
  name       = "uptimekuma.affordablepotatoes.com"
  ip_address = "100.89.157.31"
}

resource "digitalocean_domain" "jellyfin" {
  name       = "jellyfin.affordablepotatoes.com"
  ip_address = "100.83.127.33"
}

resource "digitalocean_droplet" "host_public" {
  image  = "ubuntu-22-10-x64"
  name   = "host-public"
  region = "fra1"
  size   = "s-1vcpu-1gb"
}
