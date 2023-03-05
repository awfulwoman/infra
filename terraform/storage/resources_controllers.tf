resource "libvirt_domain" "controllervm" {
  name   = var.controllervm_name
  memory = var.controllervm_ram
  vcpu   = var.controllervm_vcpus

  cloudinit = libvirt_cloudinit_disk.controllervm_cloud_init.id

  network_interface {
    network_id     = libvirt_network.network.id
    hostname       = "${var.controllervm_name}.${var.domain_name}"
    addresses      = var.controllervm_ip
    mac            = "AA:BB:CC:11:22:23"
    wait_for_lease = true
  }

  disk {
    volume_id = libvirt_volume.controllervm-base-qcow2.id
  }

  dynamic "disk" {
    for_each = range(var.controllervm_storage_volume_count)
    content {
      volume_id = libvirt_volume.controllervm-storage-volume-qcow2[disk.value].id
    }
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
