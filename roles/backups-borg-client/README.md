# backups-borg-client

Installs Borg backup on a host and configures a daily systemd timer to back up all ZFS datasets with `policy: high` or `policy: critical` to a Hetzner Storage Box.

Policy inheritance and runtime child discovery (`snapshots_discover_children`) are both honoured — the backup script discovers Docker-created child datasets at runtime and includes their mountpoints.

See [Offsite Backups](../../docs/offsite-backups.md) for the broader strategy and Storage Box setup steps.

## Variables

### Required (no defaults)

| Variable | Description |
|---|---|
| `borg_storage_box_host` | Storage Box hostname, e.g. `u123456.your-storagebox.de` |
| `borg_storage_box_user` | Storage Box username, e.g. `u123456` |
| `vault_borg_passphrase` | Borg encryption passphrase (Ansible Vault) |

### Optional

| Variable | Default | Description |
|---|---|---|
| `borg_storage_box_port` | `23` | SSH port |
| `borg_repo_path` | `./backups/{{ inventory_hostname }}` | Repo path on storage box (relative to home) |
| `borg_ssh_key_path` | `/root/.ssh/borg_ed25519` | SSH private key path |
| `borg_passphrase_file` | `/etc/borg/passphrase` | Passphrase file path on host |
| `borg_config_dir` | `/etc/borg` | Config directory |
| `borg_keep_daily` | `7` | Daily archives to keep |
| `borg_keep_weekly` | `4` | Weekly archives to keep |
| `borg_keep_monthly` | `6` | Monthly archives to keep |
| `borg_keep_yearly` | `2` | Yearly archives to keep |
| `borg_backup_hour` | `2` | Timer hour (0–23) |
| `borg_backup_minute` | `30` | Timer minute (0–59) |

## Host vars example

```yaml
borg_storage_box_host: u123456.your-storagebox.de
borg_storage_box_user: u123456
vault_borg_passphrase: !vault |
  $ANSIBLE_VAULT;1.2;AES256;beanpod
  ...
```

Generate the passphrase with:

```bash
ansible-vault encrypt_string "$(openssl rand -hex 32)" --name 'vault_borg_passphrase'
```

## SSH key setup

The role generates an ed25519 keypair at `borg_ssh_key_path` (idempotent). The public key is printed during role application — add it to the Storage Box authorized keys via the Hetzner Robot panel or sub-account SSH key management.

To retrieve it manually afterwards:

```bash
cat /root/.ssh/borg_ed25519.pub
```

## Borg commands

All commands below are run as root on the host. The `BORG_*` environment variables are set in the backup script; for manual use set them in your shell:

```bash
export BORG_REPO="ssh://u123456@u123456.your-storagebox.de:23/./backups/$(hostname)"
export BORG_PASSPHRASE="$(< /etc/borg/passphrase)"
export BORG_RSH="ssh -i /root/.ssh/borg_ed25519 -o BatchMode=yes"
```

### List archives

```bash
borg list
```

### List files in an archive

```bash
borg list ::hostname-2026-01-15T02:30:00
```

### Extract a single file or directory

```bash
# Dry run first
borg extract --dry-run --list ::hostname-2026-01-15T02:30:00 path/to/file

# Extract to current directory (strip leading /)
borg extract ::hostname-2026-01-15T02:30:00 path/to/file
```

### Mount an archive for browsing

```bash
mkdir /mnt/borg
borg mount ::hostname-2026-01-15T02:30:00 /mnt/borg
ls /mnt/borg
borg umount /mnt/borg
```

### Check repository integrity

```bash
borg check --progress
```

### Repository info

```bash
borg info
```

### Run backup manually

```bash
/usr/local/sbin/borg-backup
```

### View backup logs

```bash
journalctl -u borg-backup.service
```

## Notes

- The repository is initialised automatically on the first backup run with `repokey-blake2` encryption. The key is stored in the repository itself (on the Storage Box), protected by the passphrase. **Back up the passphrase** — without it the repository cannot be decrypted.
- Parent datasets with `snapshots_discover_children: true` (e.g. `fastpool/compositions` for Docker volumes) are expanded at backup time via `zfs list -r`. Child datasets created after role deployment are included automatically.
- Where a parent dataset's mountpoint contains child dataset mountpoints, Borg deduplicates by content so data is not stored twice, though archive metadata may reference the same files under multiple paths.
