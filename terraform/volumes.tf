# resource "libvirt_volume" "base" {
#   name = "base"
#   pool = "k8s-pool"
#   source = "/tank/images/k8s-pool/ubuntu-22.04-minimal-cloudimg-amd64.qcow2"
#   format = "qcow2"
# }