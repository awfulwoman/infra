# Base Worker VM Image
resource "libvirt_volume" "workervm_source_image" {
  name   = "workervm_source_image"
  source = "/slowpool/images/cloud/jammy-server-cloudimg-amd64-disk-kvm.img"
}

# Create Worker VM Image
resource "libvirt_volume" "workervm-base-qcow2" {
  count = 3
  name = "${var.workervm_prefix}_${format("%02d", count.index + 1)}.qcow2"
  pool = var.pool_name
  base_volume_id = libvirt_volume.workervm_source_image.id
  format = "qcow2"
  depends_on = [
    libvirt_pool.pool,
  ]
}

# Worker VMs
# Replace with a foreach loop
resource "libvirt_domain" "workervm" {
  name   = "${var.workervm_prefix}_${format("%02d", count.index + 1)}"
  memory = var.workervm_ram
  vcpu   = var.workervm_vcpus
  count = 3

  cloudinit = libvirt_cloudinit_disk.workervm_cloud_init.id

  network_interface {
    network_id     = libvirt_network.network.id
    hostname       = "${var.workervm_prefix}_${format("%02d", count.index + 1)}.${var.domain_name}"
    addresses      = var.workervm_ip
    mac            = "AA:BB:CC:11:22:22"
    wait_for_lease = true
  }

  disk {
	volume_id = "${element(libvirt_volume.workervm-base-qcow2.*.id, count.index)}"
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
