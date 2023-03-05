resource "libvirt_volume" "workervm-base-qcow2" {
  name = "${var.workervm_name}.qcow2"
  pool = var.pool_name
  source = var.workervm_source_image 
  format = "qcow2"
  depends_on = [
    libvirt_pool.pool,
  ]
}
