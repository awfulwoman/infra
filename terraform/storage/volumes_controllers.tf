resource "libvirt_volume" "controllervm-storage-volume-qcow2" {
  count = var.controllervm_storage_volume_count
  name = "controller_storage.volume.${count.index}.qcow2"
  pool = var.pool_name
  format = "qcow2"
  size =  var.controllervm_storage_volume_size
  depends_on = [
    libvirt_pool.pool,
  ]
}

resource "libvirt_volume" "controllervm-base-qcow2" {
  name = "${var.controllervm_name}.qcow2"
  pool = var.pool_name
  source = var.controllervm_source_image 
  format = "qcow2"
  depends_on = [
    libvirt_pool.pool,
  ]
}
