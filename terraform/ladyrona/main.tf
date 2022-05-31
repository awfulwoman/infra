resource "libvirt_domain" "kubernetes-controller" {
  name = "terraform_test"
  memory = "1024"
  vcpu   = 1
}

resource "libvirt_domain" "kubernetes-worker" {
  name = "terraform_test"
  memory = "1024"
  vcpu   = 1
}