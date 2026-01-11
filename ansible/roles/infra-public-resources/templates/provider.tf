provider "digitalocean" {
  token = var.digitalocean_token
}

provider "hcloud" {
  token = var.hcloud_token
}
