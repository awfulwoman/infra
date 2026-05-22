# Ubuntu cloud-init

Writes a cloud-init seed to a FAT32 USB drive labeled `cidata`, for provisioning a fresh Ubuntu Server (x86/arm64) on first boot.

## How it works

Ubuntu Server's cloud-init `nocloud` datasource automatically reads `user-data` and `meta-data` from any mounted volume labeled `cidata`. Plug the USB in alongside the machine on first boot — cloud-init picks it up, configures the system, then ignores the USB on all subsequent boots (keyed on `instance-id` in `meta-data`).

## Preparing the USB drive

Format a USB drive as FAT32 and label it `cidata`. On macOS:

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
