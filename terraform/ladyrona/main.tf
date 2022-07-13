provider "libvirt" {
   uri = "qemu+ssh://ubuntu@192.168.1.116/system"
}

resource "libvirt_network" "network" {
  name = var.network_name
  mode = "nat"
  addresses = var.network_cidr
  domain = var.domain_name
  dns {
    enabled = true
    local_only = true
  }
  dhcp {enabled = true}
}

resource "libvirt_pool" "pool" {
  name = var.pool_name
  type = "dir"
  path = "/slowpool/pools/${var.pool_name}"
}

resource "libvirt_volume" "clientVM-base-qcow2" {
  name = "${var.clientVM_name}.qcow2"
  pool = var.pool_name
  source = var.clientVM_source_image 
  format = "qcow2"
  depends_on = [
    libvirt_pool.pool,
  ]
}

resource "libvirt_cloudinit_disk" "clientVM_cloud_init" {
  name = "${var.clientVM_name}_cloud_init.iso"
  pool = var.pool_name
  user_data = data.template_file.cloud_init_template.rendered
  depends_on = [
    libvirt_pool.pool,
  ]
}

data "template_file" "cloud_init_template" {
  template = "${file("${path.module}/cloud_init.tpl")}"

  vars = {
    name = var.username
    authorized_key = var.ssh_key
  }

  depends_on = [
    libvirt_pool.pool,
  ]
}

resource "libvirt_domain" "clientVM" {
  name   = var.clientVM_name
  memory = var.clientVM_ram
  vcpu   = var.clientVM_vcpus

  cloudinit = libvirt_cloudinit_disk.clientVM_cloud_init.id

  network_interface {
    network_id     = libvirt_network.network.id
    hostname       = "${var.clientVM_name}.${var.domain_name}"
    addresses      = var.clientVM_ip
    mac            = "AA:BB:CC:11:22:22"
    wait_for_lease = true
  }

  disk {
    volume_id = libvirt_volume.clientVM-base-qcow2.id
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

resource "libvirt_volume" "serverVM-base-qcow2" {
  name = "${var.serverVM_name}.qcow2"
  pool = var.pool_name
  source = var.serverVM_source_image 
  format = "qcow2"
  depends_on = [
    libvirt_pool.pool,
  ]
}

resource "libvirt_cloudinit_disk" "serverVM_cloud_init" {
  name = "${var.serverVM_name}_cloud_init.iso"
  pool = var.pool_name
  user_data = data.template_file.cloud_init_template.rendered
  depends_on = [
    libvirt_pool.pool,
  ]
}

data "template_file" "serverVM_cloud_init_template" {
  template = "${file("${path.module}/cloud_init.tpl")}"

  vars = {
    name = var.username
    authorized_key = var.ssh_key
  }

  depends_on = [
    libvirt_pool.pool,
  ]
}

resource "libvirt_volume" "serverVM-storage-volume-qcow2" {
  count = var.serverVM_storage_volume_count
  name = "server_storage.volume.${count.index}.qcow2"
  pool = var.pool_name
  format = "qcow2"
  size =  var.serverVM_storage_volume_size
  depends_on = [
    libvirt_pool.pool,
  ]
}

resource "libvirt_domain" "serverVM" {
  name   = var.serverVM_name
  memory = var.serverVM_ram
  vcpu   = var.serverVM_vcpus

  cloudinit = libvirt_cloudinit_disk.serverVM_cloud_init.id

  network_interface {
    network_id     = libvirt_network.network.id
    hostname       = "${var.serverVM_name}.${var.domain_name}"
    addresses      = var.serverVM_ip
    mac            = "AA:BB:CC:11:22:23"
    wait_for_lease = true
  }

  disk {
    volume_id = libvirt_volume.serverVM-base-qcow2.id
  }

  dynamic "disk" {
    for_each = range(var.serverVM_storage_volume_count)
    content {
      volume_id = libvirt_volume.serverVM-storage-volume-qcow2[disk.value].id
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

# resource "libvirt_domain" "kubernetes-controller" {
#   name = "kubernetes-controller"
#   memory = "1024"
#   vcpu   = 1
# }

# resource "libvirt_domain" "kubernetes-worker" {
#   name = "kubernetes-worker"
#   memory = "1024"
#   vcpu   = 1
# }
