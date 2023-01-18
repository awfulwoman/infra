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
