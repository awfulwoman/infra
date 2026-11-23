# infra-private-resources

Manages the virtual machines that live on a hypervisor, using Terraform and
libvirt.

## Architecture

**Everything runs on the hypervisor** (`server-64gb-storage`): Terraform, the
libvirt daemon and the guests it manages.

Terraform reaches libvirt over the daemon's unix socket
(`qemu:///system`), so there is no SSH trust chain between the machine that
decides what should exist and the machine that runs it. The Terraform state
lives in the hypervisor's `fastpool/terraform` dataset.

The provider's client is pure Go and speaks the libvirt remote protocol
directly. It needs neither `virsh` nor `libvirt-clients` on the host, only
permission to open `/var/run/libvirt/libvirt-sock`.

### Why the hypervisor and not a separate control plane

An earlier version of this role ran Terraform on `deedee` and reached libvirt
over `qemu+ssh://`. It never worked, for two reasons that only show up once you
look at how the provider connects:

- The provider opens a **direct-streamlocal channel** to the libvirt socket.
  A forced command in `authorized_keys` is not run for that kind of channel,
  so the wrapper that was supposed to confine the account to libvirt did not
  confine it, while the `restrict` option (which disables port forwarding)
  blocked the connection outright.
- The account needed its own key on the hypervisor and its own
  `known_hosts` entry on the control plane, and the key had to be
  distributed to the hypervisor for the account to be usable at all.

Running the same software on the same machine removes that whole class of
problem.

## Networks

A VM's `network_mode` decides where its network sits.

| Mode | Address | Reachability | Use it for |
|------|---------|--------------|------------|
| `lan` | on the home network, e.g. `192.168.1.210` | everywhere: the fleet, the controller, the tailnet | A guest that should look like a physical machine. |
| `nat` | on the hypervisor's private libvirt network, `192.168.122.0/24` | the hypervisor, and anything that can jump through it | A guest that serves the hypervisor (NFS) at line speed. |

`lan` is macvtap: the guest sits on the same wire as the hypervisor with its
own MAC and address. The hypervisor cannot reach such a guest itself, because
macvtap has no hairpin - that only matters for a guest the hypervisor talks
to.

`nat` is the libvirt default network, which `virtual-qemu-host` defines,
starts and marks for autostart.

## Storage

Each VM gets its own libvirt storage pool: a directory under
`infra_privateresources_pool_path`, which is a ZFS dataset
(`fastpool/pools/vms`) on the hypervisor. A guest's disk is therefore
snapshotted with everything else on that pool, and the role refuses to run
if the path is not a ZFS mountpoint - a plain directory would put a guest's
disk on the root filesystem, unsnapshotted and unreplicated.

## Variables

```yaml
# The libvirt connection. The default is the local daemon's unix socket.
infra_privateresources_libvirt_uri: "qemu:///system"

# The interface a "lan" VM is bridged onto.
infra_privateresources_bridge_interface: "{{ host_primary_interface }}"

# Where the guests' disks live.
infra_privateresources_pool_path: "/fastpool/pools/vms"

# The guests.
infra_privateresources_vms:
  - id: resolute
    name: "vm-resolute"
    description: "Ubuntu 26.04 test VM"
    source_image_url: "https://cloud-images.ubuntu.com/resolute/current/resolute-server-cloudimg-amd64.img"
    memory: 4096   # MiB
    vcpus: 2
    disk_size_gb: 40
    network_mode: lan
    ip_address: "192.168.1.210"
    subnet: 24
    gateway: "192.168.1.1"
    dns: "192.168.1.1"
    mac_address: "52:54:00:00:03:01"
    graphics: false
    # Extra empty disks. Each is attached with a serial, so the guest sees it
    # at /dev/disk/by-id/virtio-<name>-data<N> for a ZFS vdev or a filesystem.
    data_disks:
      - size_gb: 20
    autostart: true
```

`name` is the libvirt domain name, the storage pool directory and the
hostname cloud-init sets. A `lan` VM's address must sit outside the DHCP
range of the home network.

## Usage

The role runs from the hypervisor's own playbook
(`playbooks/hosts/server-64gb-storage/core.yaml`).

```bash
# Plan only, and show what it would do.
ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml \
  --tags infra-private-resources \
  -e infra_privateresources_debug=true \
  -e infra_privateresources_tf_plan_only=true
```

By default the role applies (`infra_privateresources_tf_apply: true`), so a
nightly run of the hypervisor's playbook keeps the fleet of guests in step
with what the repository declares.

### Manual Terraform

```bash
cd /fastpool/terraform/private-resources
./tf plan
./tf apply -auto-approve
```

## Dependencies

- `virtual-qemu-host`: runs on the hypervisor first, and must come before
  this role in the playbook. It installs libvirt, defines the default
  network and makes sure it is running.
- `system-zfs`: creates the dataset the guests' disks live in.

## Files Managed

### On the hypervisor

- `/fastpool/terraform/private-resources/` - Terraform configuration and
  state
- `/fastpool/pools/vms/<vm>/` - each guest's storage pool

## Adding a guest

1. Add it to `infra_privateresources_vms` in
   `roles/infra-private-resources/defaults/main.yaml`.
2. Give it a host entry in `inventory/hosts.yaml`, a `host_vars` directory
   and a playbook in `playbooks/hosts/`, if Ansible is to manage it.
3. Run the hypervisor's playbook. Terraform creates the guest; the guest's
   own playbook configures it.
