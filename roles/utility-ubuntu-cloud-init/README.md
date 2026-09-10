# Ubuntu cloud-init

Writes a cloud-init seed to a FAT32 USB drive labeled `cidata`, to provision a fresh Ubuntu Server (x86/arm64) on first boot.

## How it works

Ubuntu Server's cloud-init `nocloud` datasource automatically reads `user-data` and `meta-data` from any mounted volume labeled `cidata`. When you plug the USB in alongside the machine on first boot, cloud-init picks it up and configures the system. It then ignores the USB on later boots. This behavior is keyed on the `instance-id` value in `meta-data`.

## Preparing the USB drive

Format a USB drive as FAT32. Label it `cidata`. On macOS:

```bash
diskutil eraseDisk FAT32 cidata /dev/diskN
```

Replace `/dev/diskN` with the correct disk (check `diskutil list`). macOS mounts it automatically at `/Volumes/cidata`.

## Running

Override `ubuntu_cloud_init_hostname` per machine:

```bash
ansible-playbook playbooks/utility/ubuntu-cloud-init.yaml \
  -e ubuntu_cloud_init_hostname=my-new-server
```

## Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ubuntu_cloud_init_mount_path` | `/Volumes/cidata` | Where the cidata USB is mounted |
| `ubuntu_cloud_init_hostname` | `ubuntu-server` | Hostname to set on first boot |
| `ubuntu_cloud_init_timezone` | `Europe/Berlin` | System timezone |
| `ubuntu_cloud_init_username` | `{{ vault_server_username }}` | User to create |
| `ubuntu_cloud_init_groups` | `users,adm,sudo` | Groups for the created user |
| `ubuntu_cloud_init_github_username` | `awfulwoman` | GitHub user to fetch SSH keys from |
| `ubuntu_cloud_init_ssh_pwauth` | `false` | Allow SSH password auth |
| `ubuntu_cloud_init_package_update` | `false` | Run `apt-get update` on first boot |
| `ubuntu_cloud_init_package_upgrade` | `false` | Run `apt-get upgrade` on first boot |
| `ubuntu_cloud_init_ip` | `""` | Static IP address — omit or leave empty for DHCP |
| `ubuntu_cloud_init_prefix` | `24` | Subnet prefix length |
| `ubuntu_cloud_init_gateway` | `""` | Default gateway |
| `ubuntu_cloud_init_interface` | `eth0` | Network interface name (check `ip link` on the target) |
| `ubuntu_cloud_init_dns` | `[1.1.1.1, 8.8.8.8]` | DNS resolvers |

## Static IP example

```bash
ansible-playbook playbooks/utility/ubuntu-cloud-init.yaml \
  -e ubuntu_cloud_init_hostname=my-new-server \
  -e ubuntu_cloud_init_ip=192.168.1.50 \
  -e ubuntu_cloud_init_gateway=192.168.1.1 \
  -e ubuntu_cloud_init_interface=enp3s0
```

## Interface names

The name in `ubuntu_cloud_init_interface` must match the target exactly. The seed writes a netplan block keyed on that name — if the name is wrong, the machine boots with no network and you have to attach a screen and keyboard.

### Raspberry Pi

Ubuntu's `preinstalled-server-arm64+raspi` images keep the old-style kernel names:

| Name | Hardware |
|------|----------|
| `eth0` | Built-in ethernet port (Pi 3, 4, 5, CM4 carrier boards) |
| `wlan0` | Built-in Wi-Fi |
| `enx001122334455` | USB ethernet adapter — `enx` plus the adapter's MAC address |
| `eth1` | USB ethernet adapter, on images where predictable names are disabled |

`eth0` is the right answer for almost every Pi.

### MiniPC and x86 servers

These use systemd predictable interface names, so the name comes from the NIC's PCI address or firmware index.

The miniPCs here are Dell Wyse 5070 thin clients — `homebrain` and `camina` are both 5070s. Their onboard Realtek RTL8111/8168 NIC sits on PCI bus 1, so it always comes up as:

```
enp1s0
```

Use `enp1s0` for any Wyse 5070. Apply the `hardware-wyse-5070` role after provisioning — it swaps the generic `r8169` kernel driver for the vendor `r8168` DKMS driver, which fixes intermittent link drops on this NIC. The interface name does not change.

Other x86 hardware:

| Name | Hardware |
|------|----------|
| `enp2s0`, `enp3s0`, `enp4s0` | Onboard NIC on a different PCI bus/slot. Multi-port boxes number them in port order |
| `enp1s0f0`, `enp1s0f1` | Multi-port NIC on an add-in card — `f0`/`f1` are the ports on one function |
| `eno1`, `eno2` | Onboard NIC where the firmware supplies an index — common on Intel NUC and business-class desktops |
| `enp0s31f6` | Intel I219 onboard NIC — frequent on ThinkCentre and older NUC |
| `ens18`, `ens3` | Virtual NIC in a Proxmox, KVM or QEMU guest |
| `enx001122334455` | USB or USB4/Thunderbolt ethernet adapter |
| `eth0` | Cloud images and some minimal installs, where predictable names are turned off |

### Finding the name

Boot the target with DHCP first (leave `ubuntu_cloud_init_ip` empty), then read the name off the machine:

```bash
ip -brief link
```

Rewrite the USB with the static settings once you know it. Both `ip link` and the boot console print the name.
