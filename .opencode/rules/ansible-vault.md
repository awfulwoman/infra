# Ansible Vault

## Never print a secret

A deploy runs with the vault unlocked, so any task that renders a vaulted value
into its result writes it, in plaintext, into the run log. Nightly runs are
readable over the API, so treat a printed secret as published.

Add `no_log: true` to a task when a secret reaches its result:

- `debug: var:` / `msg:` naming a secret
- `assert: fail_msg:` or `fail: msg:` interpolating one
- `command` / `shell` with a secret in the command line — Ansible prints the
  whole `cmd` when the task fails
- any module whose arguments hold a secret, when you need it on failure

`no_log` hides the whole task result, so keep it off where the output is the
point and print something derived instead. It does not affect `register`: the
variable is still populated and usable in `when` / `failed_when`.

`scripts/validate-secret-logging.py` enforces this in pre-commit over `roles/`
and `playbooks/`. It matches variable *names* (`vault_*`, and names ending
`_password`, `_token`, `_secret`, `_key`), so a badly named variable hides a
leak — name secrets accordingly.

## Generating a secret

When instructing the user to encrypt a secret with `ansible-vault encrypt_string`, always embed a secret-generation command inline rather than using a placeholder. Use `openssl rand -hex 32` for passwords and encryption keys:

```bash
ansible-vault encrypt_string "$(openssl rand -hex 32)" --name 'vault_example_key'
```
