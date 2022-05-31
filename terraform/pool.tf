# This is the same as the following command:
# virsh pool-define-as default --type dir --target /tank/pools/default
# https://unix.stackexchange.com/questions/216837/virsh-and-creating-storage-pools-what-is-sourcepath
# It creates a directory and assigns it to the libvirt pool named "default"

resource "libvirt_pool" "default" {
  name = "default"
  type = "dir"
  path = "/tank/pools/default"
}

# pool-define-as --name default --source-name filepool --type zfs
# It takes a ZFS pool and assigns it in totality to the libvirt pool named "default"
# The Terraform provider does not yet support ZFS pools so this would have to be done manually.