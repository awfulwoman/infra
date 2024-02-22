variable "digitalocean_token" {
  description = "The digital ocean API token"
  type = string
  sensitive = true
}

variable "domain_name" {
  description = "The home automation domain name"
  type = string
  sensitive = true
}

variable "tailscale_ip_host_storage" {
  description = "The IP address for this server on Tailscale"
  type = string
  default = "100.83.127.33"
}

variable "tailscale_ip_host_homeautomation" {
  description = "The IP address for this server on Tailscale"
  type = string
  default = "100.66.127.130"
}