# System Ubuntu Pro

Attaches or detaches an Ubuntu host from an Ubuntu Pro subscription with the `pro` CLI.

Ubuntu Pro provides access to extended security maintenance (ESM), kernel livepatch, and other security features beyond the standard Ubuntu support lifecycle. This role is idempotent. It checks the current attachment status before it acts. It runs `pro attach` or `pro detach` only when the state must change.

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `ubuntupro_attach` | `false` | Set to `true` to attach, `false` to detach |
| `ubuntupro_debug` | `false` | Print `pro attach/detach` output for debugging |
| `vault_ubuntupro_token` | _(required)_ | Ubuntu Pro token from `ubuntu.com/pro` — stored in Ansible Vault |

## Design Notes

- `ubuntupro_attach: false` is the safe default. It avoids the accidental attachment of hosts that you do not want to enroll.
- The role expects the token in `vault_ubuntupro_token` (encrypted in Ansible Vault). If this variable is undefined, the role takes no action.
- The role reads the attachment status with `pro status --format json` at the start of every run. This keeps the role fully idempotent.
- The `system-security` role reads the attachment status that this role sets, to decide whether to include ESM origins in the unattended-upgrades configuration. If you want ESM updates, run this role before `system-security`.
- This role requires Linux (enforced by the `ansible-assert-platform` dependency in `meta/main.yaml`).
