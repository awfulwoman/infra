variable "digitalocean_token" {
  description = "The digital ocean API token"
  type = string
  sensitive = true
  default=""
}

variable "domain_name" {
  description = "The home automation domain name"
  type = string
  sensitive = true
  default=""
}

variable "tailscale_ip_host_storage" {
  description = "The IP address for the storage server on Tailscale"
  type = string
  default = "100.83.127.33"
}

variable "tailscale_ip_host_homeautomation" {
  description = "The IP address for the generic home automation server on Tailscale"
  type = string
  default = "100.66.127.130"
}

variable "tailscale_ip_host_mqtt" {
  description = "The IP address for the MQTT server on Tailscale"
  type = string
  default = "100.104.51.6"
}

variable "tailscale_ip_host_radio" {
  description = "The IP address for the radio server on Tailscale"
  type = string
  default = "100.105.190.86"
}