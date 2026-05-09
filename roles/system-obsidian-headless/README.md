# system-obsidian-headless

Installs and runs [obsidian-headless](https://github.com/obsidianmd/obsidian-headless) as a background sync service, keeping configured vaults continuously synced via Obsidian Sync.

## Prerequisites

- `system-nvm` must be applied to the target host first — obsidian-headless is installed via the nvm-managed `npm`.
- An active [Obsidian Sync](https://obsidian.md/sync) subscription.
- **Manual one-time step**: log in on the target host before running this role:
  ```
  ob login
  ```
  Credentials are stored in the system keychain (Keychain on macOS, libsecret on Linux). The role does not handle login — MFA and interactive prompts make it unautomatable.

## What it does

- Installs `obsidian-headless` globally via the nvm-managed `npm`.
- Logs in to your Obsidian account and configures each vault for sync.
- **Ubuntu/Debian**: manages a systemd service (`obsidian-headless.service`).
- **macOS**: manages a per-user LaunchAgent (`com.awfulwoman.obsidian-headless`).

## Variables

See `defaults/main.yaml`.

| Variable | Default | Description |
|---|---|---|
| `system_obsidian_headless_vaults` | `[]` | Vaults to sync (see below) |
| `system_obsidian_headless_device_name` | `{{ inventory_hostname }}` | Device name shown in Obsidian Sync |
| `system_obsidian_headless_user` | current ansible user | User that owns vaults and runs the service |

### Vault list format

```yaml
system_obsidian_headless_vaults:
  - name: "My Vault"
    path: "/home/user/notes"
  - name: "Work Notes"
    path: "/home/user/work"
    password: "{{ vault_work_notes_password }}"  # only if E2E encrypted
```

## Example

```yaml
- hosts: host-generic-64gb-storage
  roles:
    - role: system-nvm
    - role: system-obsidian-headless
      vars:
        system_obsidian_headless_vaults:
          - name: "Notes"
            path: "/home/ubuntu/notes"
```

## Platforms

- Ubuntu/Debian (systemd)
- macOS (launchd)
