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
      version = "2.28.1"
    }
  }
}

provider "digitalocean" {
  token = var.digitalocean_token
}

resource "digitalocean_domain" "default" {
   name = "affordablepotatoes.com"
}


# output "domain_output" {
#   value = data.digitalocean_domain.default.zone_file
# }
# Nameservers
# resource "digitalocean_record" "ns1" {
#   domain = digitalocean_domain.default.id
#   type   = "NS"
#   value   = "ns1.digitalocean.com."
#   name  = "@"
# }

# resource "digitalocean_record" "ns2" {
#   domain = digitalocean_domain.default.id
#   type   = "NS"
#   value   = "ns2.digitalocean.com."
#   name  = "@"
# }

# resource "digitalocean_record" "ns3" {
#   domain = digitalocean_domain.default.id
#   type   = "NS"
#   value   = "ns3.digitalocean.com."
#   name  = "@"
# }


# Home Automation
resource "digitalocean_record" "homeassistant" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "homeassistant"
  value  = "100.66.127.130"
}

resource "digitalocean_record" "homeautomation" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "homeautomation"
  value  = "100.66.127.130"
}

resource "digitalocean_record" "esphome" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "esphome"
  value  = "100.66.127.130"
}

resource "digitalocean_record" "zigbee2mqtt" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "zigbee2mqtt"
  value  = "100.66.127.130"
}

resource "digitalocean_record" "zigbee2mqtt-aqara" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "zigbee2mqtt-aqara"
  value  = "100.66.127.130"
}

resource "digitalocean_record" "uptimekuma" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "uptimekuma"
  value  = "100.66.127.130"
}


# Storage
resource "digitalocean_record" "jellyfin" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "jellyfin"
  value  = "100.83.127.33"
}

resource "digitalocean_record" "gluetun" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "gluetun"
  value  = "100.83.127.33"
}

resource "digitalocean_record" "sonarr" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "sonarr"
  value  = "100.83.127.33"
}

resource "digitalocean_record" "radarr" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "radarr"
  value  = "100.83.127.33"
}

resource "digitalocean_record" "lidarr" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "lidarr"
  value  = "100.83.127.33"
}

resource "digitalocean_record" "prowlarr" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "prowlarr"
  value  = "100.83.127.33"
}

resource "digitalocean_record" "readarr" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "readarr"
  value  = "100.83.127.33"
}

resource "digitalocean_record" "podgrab" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "podgrab"
  value  = "100.83.127.33"
}

resource "digitalocean_record" "audiobookshelf" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "audiobookshelf"
  value  = "100.83.127.33"
}

resource "digitalocean_record" "copyparty" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "copyparty"
  value  = "100.83.127.33"
}

resource "digitalocean_record" "freshrss" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "freshrss"
  value  = "100.83.127.33"
}

resource "digitalocean_record" "wallabag" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "wallabag"
  value  = "100.83.127.33"
}

resource "digitalocean_record" "syncthing" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "syncthing"
  value  = "100.83.127.33"
}

resource "digitalocean_record" "shiori" {
  domain = digitalocean_domain.default.id
  type   = "A"
  name   = "shiori"
  value  = "100.83.127.33"
}

# resource "digitalocean_droplet" "host_public" {
#   image  = "ubuntu-22-10-x64"
#   name   = "host-public"
#   region = "fra1"
#   size   = "s-1vcpu-1gb"
# }
