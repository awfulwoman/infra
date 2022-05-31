provider "libvirt" {
   uri = "qemu+ssh://ubuntu@192.168.1.116/system"
}

resource "libvirt_pool" "default-pool" {
  name = "default-pool"
  type = "dir"
  path = "/tank/terraform-provider-libvirt-pool-default"
}

resource "libvirt_volume" "server_data_disk" {
  name  = "server-data-disk"
  size  = 32
  pool  = default-pool
}

# data "template_file" "user_data" {
#   template = file("${path.module}/cloud_init.cfg")
# }

# data "template_file" "network_config" {
#   template = file("${path.module}/network_config.cfg")
# }

# # for more info about paramater check this out
# # https://github.com/dmacvicar/terraform-provider-libvirt/blob/master/website/docs/r/cloudinit.html.markdown
# # Use CloudInit to add our ssh-key to the instance
# # you can add also meta_data field
# resource "libvirt_cloudinit_disk" "commoninit" {
#   name           = "commoninit.iso"
#   user_data      = data.template_file.user_data.rendered
#   network_config = data.template_file.network_config.rendered
#   pool           = libvirt_pool.default.name
# }

# Create the machine
resource "libvirt_domain" "domain-ubuntu" {
  name   = "ubuntu-terraform"
  memory = "512"
  vcpu   = 1

  # cloudinit = libvirt_cloudinit_disk.commoninit.id

  # network_interface {
  #   network_name = "default"
  # }

  # # IMPORTANT: this is a known bug on cloud images, since they expect a console
  # # we need to pass it
  # # https://bugs.launchpad.net/cloud-images/+bug/1573095
  # console {
  #   type        = "pty"
  #   target_port = "0"
  #   target_type = "serial"
  # }

  # console {
  #   type        = "pty"
  #   target_type = "virtio"
  #   target_port = "1"
  # }

  # disk {
  #   volume_id = libvirt_volume.ubuntu-qcow2.id
  # }

  # graphics {
  #   type        = "spice"
  #   listen_type = "address"
  #   autoport    = true
  # }
}

terraform {
  required_version = ">= 0.12"
}