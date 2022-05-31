provider "libvirt" {
   uri = "qemu+ssh://ubuntu@192.168.1.116/system"
}

resource "libvirt_pool" "pool" {
  name = "default-pool"
  type = "dir"
  path = "/tank/terraform-provider-libvirt-pool-default"
}

resource "libvirt_volume" "server_data_disk" {
  name  = "server-data-disk"
  size  = 32
  pool  = pool.id
}

# Create the machine
resource "libvirt_domain" "domain-ubuntu" {
  name   = "ubuntu-terraform"
  memory = "512"
  vcpu   = 1
}

terraform {
  required_version = ">= 0.12"
}