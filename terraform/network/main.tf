terraform {
  cloud {
    organization = "whalecoiner"
    workspaces {
      name = "affordablepotatoes_subdomains"
    }
  }
}

terraform {
  required_providers {
    digitalocean = {
      source = "digitalocean/digitalocean"
      version = "2.34.1"
    }
  }
}

provider "digitalocean" {
  token = var.digitalocean_token
}

resource "digitalocean_domain" "default" {
   name = var.domain_name
}

resource "digitalocean_project" "network" {
  name        = "Home Network"
  description = "Networking for the home."
  purpose     = "Web Application"
  environment = "Production"
}

resource "digitalocean_project_resources" "network" {
  project = digitalocean_project.network.id
  resources = [
    digitalocean_domain.default.urn
  ]
}

# data "digitalocean_domain" "default" {
#   name = var.domain_name
# }

# output "domain_output" {
#   value = data.digitalocean_domain.default.zone_file
# }

# Home Automation
resource "digitalocean_record" "root" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "@"
  value  = var.tailscale_ip_host_homeautomation
}

# Nameservers
resource "digitalocean_record" "ns1" {
  domain = digitalocean_domain.default.id
  type   = "NS"
  value   = "ns1.digitalocean.com."
  name  = "@"
}

resource "digitalocean_record" "ns2" {
  domain = digitalocean_domain.default.id
  type   = "NS"
  value   = "ns2.digitalocean.com."
  name  = "@"
}

resource "digitalocean_record" "ns3" {
  domain = digitalocean_domain.default.id
  type   = "NS"
  value   = "ns3.digitalocean.com."
  name  = "@"
}


# Home Automation
resource "digitalocean_record" "homeassistant" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "homeassistant"
  value  = var.tailscale_ip_host_homeautomation
}

resource "digitalocean_record" "homeautomation" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "homeautomation"
  value  = var.tailscale_ip_host_homeautomation
}

resource "digitalocean_record" "esphome" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "esphome"
  value  = var.tailscale_ip_host_homeautomation
}

resource "digitalocean_record" "mqtt" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "mqtt"
  value  = var.tailscale_ip_host_homeautomation
}

resource "digitalocean_record" "zigbee2mqtt" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "zigbee2mqtt"
  value  = var.tailscale_ip_host_homeautomation
}

resource "digitalocean_record" "zigbee2mqtt-aqara" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "zigbee2mqtt-aqara"
  value  = var.tailscale_ip_host_homeautomation
}

resource "digitalocean_record" "uptimekuma" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "uptimekuma"
  value  = var.tailscale_ip_host_homeautomation
}

resource "digitalocean_record" "traefik-host-homeautomation" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "traefik.host-homeautomation"
  value  = var.tailscale_ip_host_homeautomation
}


# Storage
resource "digitalocean_record" "jellyfin" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "jellyfin"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "qbittorrent" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "qbittorrent"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "gluetun" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "gluetun"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "sonarr" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "sonarr"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "radarr" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "radarr"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "lidarr" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "lidarr"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "prowlarr" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "prowlarr"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "readarr" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "readarr"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "podgrab" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "podgrab"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "audiobookshelf" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "audiobookshelf"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "copyparty" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "copyparty"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "freshrss" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "freshrss"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "wallabag" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "wallabag"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "syncthing" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "syncthing"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "shiori" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "shiori"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "bookmarks" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "bookmarks"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "gitea" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "gitea"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "jellyfin-vue" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "jellyfin-vue"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "pinry" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "pinry"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "bazarr" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "bazarr"
  value  = var.tailscale_ip_host_storage
}

resource "digitalocean_record" "traefik-host-storage" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "traefik.host-storage"
  value  = var.tailscale_ip_host_storage
}

# resource "digitalocean_droplet" "host_public" {
#   image  = "ubuntu-22-10-x64"
#   name   = "host-public"
#   region = "fra1"
#   size   = "s-1vcpu-1gb"
# }
