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