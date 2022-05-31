
resource "libvirt_domain" "terraform_test" {
  name = "terraform_test"
  memory = "1024"
  vcpu   = 1
}