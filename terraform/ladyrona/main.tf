resource "libvirt_domain" "kubernetes-controller" {
  name = "kubernetes-controller"
  memory = "1024"
  vcpu   = 1
}

resource "libvirt_domain" "kubernetes-worker" {
  name = "kubernetes-worker"
  memory = "1024"
  vcpu   = 1
}
