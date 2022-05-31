resource "libvirt_pool" "cluster" {
  name = "k8s-pool"
  type = "dir"
  path = "/tank/images"
}