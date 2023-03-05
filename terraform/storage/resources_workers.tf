

resource "libvirt_domain" "workervm" {
  name   = var.workervm_name
  memory = var.workervm_ram
  vcpu   = var.workervm_vcpus

  cloudinit = libvirt_cloudinit_disk.workervm_cloud_init.id

  network_interface {
    network_id     = libvirt_network.network.id
    hostname       = "${var.workervm_name}.${var.domain_name}"
    addresses      = var.workervm_ip
    mac            = "AA:BB:CC:11:22:22"
    wait_for_lease = true
  }

  disk {
    volume_id = libvirt_volume.workervm-base-qcow2.id
  }

  console {
    type = "pty"
    target_type = "serial"
    target_port = "0"
  }

  graphics {
    type = "spice"
    listen_type = "address"
    autoport = true
  }
}
