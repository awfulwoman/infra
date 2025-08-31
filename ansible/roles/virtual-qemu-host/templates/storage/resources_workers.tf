# Grab Worker base VM Image
# Source: https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64-disk-kvm.img
resource "libvirt_volume" "ubuntu_jammy_image" {
  name   = "workervm_source_image"
  source = "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64-disk-kvm.img"
  pool = var.pool_name
  depends_on = [
    libvirt_pool.pool,
  ]
}

# Create Worker VM Disk Images
resource "libvirt_volume" "workervm_disk_image" {
  count = var.workervm_count
  name = "${var.workervm_prefix}_${format("%02d", count.index + 1)}.qcow2"
  pool = var.pool_name
  base_volume_id = libvirt_volume.ubuntu_jammy_image.id
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
  count = var.workervm_count

  cloudinit = libvirt_cloudinit_disk.workervm_cloud_init.id

  network_interface {
    network_id     = libvirt_network.network.id
    hostname       = "${var.workervm_prefix}_${format("%02d", count.index + 1)}.${var.domain_name}"
    addresses      = ["192.168.100.1${format("%02d", count.index + 1)}"]
    wait_for_lease = true
  }

  disk {
	  volume_id = "${element(libvirt_volume.workervm_disk_image.*.id, format("%02d", count.index + 1))}"
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
