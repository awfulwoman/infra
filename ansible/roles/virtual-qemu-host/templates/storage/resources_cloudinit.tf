
resource "libvirt_cloudinit_disk" "workervm_cloud_init" {
  name = "${var.workervm_prefix}_cloud_init.iso"
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


resource "libvirt_cloudinit_disk" "controllervm_cloud_init" {
  name = "${var.controllervm_name}_cloud_init.iso"
  pool = var.pool_name
  user_data = data.template_file.cloud_init_template.rendered
  depends_on = [
    libvirt_pool.pool,
  ]
}

data "template_file" "controllervm_cloud_init_template" {
  template = "${file("${path.module}/cloud_init.tpl")}"

  vars = {
    name = var.username
    authorized_key = var.ssh_key
  }

  depends_on = [
    libvirt_pool.pool,
  ]
}
