# resource "libvirt_volume" "base" {
#   name = "base"
#   pool = "k8s-pool"
#   source = "/slowpool/images/k8s-pool/ubuntu-22.04-minimal-cloudimg-amd64.qcow2"
#   format = "qcow2"
# }


# resource "libvirt_volume" "ubuntu_jammy" {
#   name = "${var.clientVM_name}.qcow2"
#   pool = var.pool_name
#   source = var.clientVM_source_image 
#   format = "qcow2"
#   depends_on = [
#     libvirt_pool.pool,
#   ]
# }

# Attach to all VMs in the terraform_test domain

# resource "libvirt_volume" "terraform_test" {
#   name           = "master.qcow2"
#   base_volume_id = libvirt_volume.opensuse_leap.id
# }