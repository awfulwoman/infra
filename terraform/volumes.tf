# resource "libvirt_volume" "base" {
#   name = "base"
#   pool = "k8s-pool"
#   source = "/tank/images/k8s-pool/ubuntu-22.04-minimal-cloudimg-amd64.qcow2"
#   format = "qcow2"
# }

resource "libvirt_volume" "opensuse_leap" {
  name = "opensuse_leap"
  pool = "default"
  source = "http://download.opensuse.org/repositories/Cloud:/Images:/Leap_42.1/images/openSUSE-Leap-42.1-OpenStack.x86_64.qcow2"
}

# Attach to all VMs in the terraform_test domain

resource "libvirt_volume" "terraform_test" {
  name           = "master.qcow2"
  base_volume_id = libvirt_volume.opensuse_leap.id
}