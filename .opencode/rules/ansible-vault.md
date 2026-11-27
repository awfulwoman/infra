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

## New secrets go to 1Password

Do not add new `vault_*` variables. Create the secret in 1Password and read it with the
`onepassword_connect` lookup (see `docs/1password-connect.md`):

1. Declare the item in `playbooks/utility/provision-secrets/<subject>.yaml`. A generated
   field (`generate: on_create`) is made inside 1Password, so no one sees the value. To copy
   an existing vault secret instead, give the field `value: "{{ vault_x }}"`.
2. The user runs `OP_CONNECT_TOKEN_WRITE=… ansible-playbook playbooks/utility/provision-secrets.yaml -e subject=<subject>`
   (`--check` first). Never store the write token or ask for it to be put in a file.
3. Read it in the role: `lookup('onepassword_connect', 'App - <App>', '<field>')`, inside a task with `no_log: true`.

Existing `vault_*` secrets stay in Ansible Vault until their migration (infra#285); the rule
above about never printing them still applies.
