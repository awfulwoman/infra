resource "libvirt_network" "network" {
  name = var.network_name
  mode = "nat"
  addresses = var.network_cidr
  domain = var.domain_name
  dns {
    enabled = true
    local_only = true
  }
  dhcp {enabled = true}
}



# resource "libvirt_domain" "kubernetes-controller" {
#   name = "kubernetes-controller"
#   memory = "1024"
#   vcpu   = 1
# }

# resource "libvirt_domain" "kubernetes-worker" {
#   name = "kubernetes-worker"
#   memory = "1024"
#   vcpu   = 1
# }
