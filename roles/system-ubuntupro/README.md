# System Ubuntu Pro

Attaches or detaches an Ubuntu host from an Ubuntu Pro subscription using the `pro` CLI.

Ubuntu Pro provides access to extended security maintenance (ESM), kernel livepatch, and other security features beyond the standard Ubuntu support lifecycle. This role is idempotent: it checks the current attachment status before acting and only runs `pro attach` or `pro detach` when a state change is actually needed.

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `ubuntupro_attach` | `false` | Set to `true` to attach, `false` to detach |
| `ubuntupro_debug` | `false` | Print `pro attach/detach` output for debugging |
| `vault_ubuntupro_token` | _(required)_ | Ubuntu Pro token from `ubuntu.com/pro` — stored in Ansible Vault |

## Design Notes

- `ubuntupro_attach: false` is the safe default to avoid accidentally attaching hosts that should not be enrolled.
- The token is expected in `vault_ubuntupro_token` (Ansible Vault encrypted). The role takes no action if this variable is undefined.
- Attachment status is read via `pro status --format json` at the start of every run so the role is fully idempotent.
- The `system-security` role reads the attachment status set by this role to conditionally include ESM origins in the unattended-upgrades configuration — run this role before `system-security` if ESM updates are required.
- Requires Linux (enforced via `ansible-assert-platform` dependency in `meta/main.yaml`).
