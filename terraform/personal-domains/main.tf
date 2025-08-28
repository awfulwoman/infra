# terraform {
#   cloud {
#     organization = "whalecoiner"
#     workspaces {
#       name = "affordablepotatoes_subdomains"
#     }
#   }
# }


# resource "digitalocean_domain" "default" {
#    name = var.domain_name
# }

resource "digitalocean_project" "personal_sites" {
  name        = "Test Project"
  description = "Personal domains and records."
  purpose     = "Web Application"
  environment = "Production"
}

# resource "digitalocean_project_resources" "personal_sites" {
#   project = digitalocean_project.personal_sites.id
#   resources = [
#     digitalocean_domain.default.urn
#   ]
# }

# data "digitalocean_domain" "default" {
#   name = var.domain_name
# }

# output "domain_output" {
#   value = data.digitalocean_domain.default.zone_file
# }


# resource "digitalocean_record" "root" {
#   domain = digitalocean_domain.default.id
#   type   = "A"
#   name   = "@"
#   value  = var.tailscale_ip_host_homeautomation
# }

# # Nameservers
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




# resource "digitalocean_record" "esphome" {
#   domain = digitalocean_domain.default.id
#   type   = "A"
#   name   = "esphome"
#   value  = var.tailscale_ip_host_homeautomation
# }


# resource "digitalocean_droplet" "host_public" {
#   image  = "ubuntu-22-10-x64"
#   name   = "host-public"
#   region = "fra1"
#   size   = "s-1vcpu-1gb"
# }
