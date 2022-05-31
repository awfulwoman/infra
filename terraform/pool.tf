resource "libvirt_pool" "default" {
  name = "default"
  type = "dir"
  path = "/tank/pools/default"
}