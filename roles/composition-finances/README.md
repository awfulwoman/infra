# Finances

This role deploys [Firefly III](https://www.firefly-iii.org/), a self-hosted personal finance manager, with its data importer for bank exports. Firefly III tracks income, expenses, budgets, and categories across multiple accounts.

## Services

| Container | Purpose | Port |
|-----------|---------|------|
| **firefly_iii_core** | Main Firefly III application | `8983` (localhost only) |
| **firefly_iii_db** | MariaDB database | — |
| **firefly_iii_importer** | CSV/CAMT data importer UI | `8111` (localhost only) |
| **cron** | Alpine cron container — triggers recurring transaction jobs daily at 03:00 | — |

## Key Variables

| Variable | Purpose |
|----------|---------|
| `vault_firefly_cron_token` | Token for the Firefly III cron endpoint |
| `vault_firefly_db_password` | MariaDB password |
| `vault_firefly_app_key` | Laravel application encryption key (32 chars) |
| `firefly_app_url` | Public URL; password-reset links are built from it |
| `firefly_mail_*` | SMTP relay (mailbox.org, port 465), shared with nullmailer |
| `firefly_log_level` | `notice` normally; `debug` to recover a reset link if SMTP breaks |
| `firefly_enablebanking_item_id` | 1Password item holding the Enable Banking credentials |

You must set the three vault variables (they default to `null`). Store them in
Ansible Vault.

## Enable Banking

The data importer talks to [Enable Banking](https://enablebanking.com/), with an
application ID and a private key, following the
[upstream tutorial](https://docs.firefly-iii.org/tutorials/data-importer/eb/).

These credentials reach live bank data. Unlike the rest of this role's
secrets, they are **not** kept in the repo, not even in Ansible Vault. They
live only in 1Password (item `fisnhyavlrcztjznla55kuzdu4`, fields `App ID` and
`Private Key`). The role fetches them through 1Password Connect on each run,
then writes them straight into `.environment_vars_importer` on the host. The
fetch is delegated to the controller, so the Connect token never reaches the
target.

1Password stores the private key as an **ordinary multi-line PEM**: the
`.pem` file's contents pasted in as-is, with real line breaks. The role
passes it through unchanged.

The upstream tutorial instead shows the key collapsed onto one line, with literal
`\n` escapes. That form is correct when the value lands in Laravel's own `.env`
file, where phpdotenv expands the escapes. It is the wrong form here: this
composition delivers the value through Docker Compose `env_file`, which does no
escape expansion. As a result, openssl would receive two literal characters
where a line break belongs. Compose keeps real newlines in a quoted `env_file`
value (confirmed on Compose v5.5.0 running on storage), so the plain PEM needs
no conversion.

The item must live in the `Infra` vault, because that is the only vault the
Connect read token can see. 1Password reassigns an item's UUID when it moves
between vaults, so you must update `firefly_enablebanking_item_id` if the item
is ever relocated. Confirm that it is visible and correctly shaped with:

```bash
ansible-playbook playbooks/utility/check-enablebanking-credentials.yaml
```

Neither `ENABLE_BANKING_IMPORT_IP_HEADER` nor `ENABLE_BANKING_IMPORT_IP` is set
here, and neither needs to be set. They control the PSD2 `PSU-IP-Address`
header, which carries the end user's real IP for strong customer
authentication. The importer reads the IP only when the header flag is `true`,
which defaults to `false`, so the header is never sent. Set both only if a
bank specifically demands it. Note that the `autodetect` value calls out to
icanhazip.com, and that a private address such as the `127.0.0.1` default
fails the importer's own public-IP check and is dropped.

## Recovering a lost password

Firefly III enforces a 16-character minimum password, and
[you cannot lower the minimum](https://docs.firefly-iii.org/references/faq/firefly-iii/using/).
There is no artisan command to set a password. The reset flow at
`https://firefly.<domain>/password/reset` is the only recovery path, which is
why the SMTP config above matters. Any replacement password must have at
least 16 characters, or the reset form rejects it.

If SMTP itself is broken, use the log mailer instead. If the log level is set
to debug, Firefly writes the mail to the container log instead of sending it.

```bash
# 1. Redeploy with the log mailer and debug logging
ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml \
  --tags composition -e target_composition=finances \
  -e firefly_mail_mailer=log -e firefly_log_level=debug

# 2. Request a reset at https://firefly.<domain>/password/reset

# 3. Read the link out of the log
ssh server-64gb-storage \
  'docker logs --since 5m firefly_iii_core 2>&1 | grep -oE "https://[^ \"<>]*password/reset/[A-Za-z0-9]+" | tail -1'

# 4. Set the new password, then redeploy without the -e overrides to
#    restore SMTP and drop the log level back to notice
ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml \
  --tags composition -e target_composition=finances
```

If the reset form refuses to issue a new token, first clear stale rows:
run `DELETE FROM password_resets;` in the `firefly` database.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/firefly-upload` | User-uploaded attachments |
| `{{ composition_config }}/firefly-db` | MariaDB data directory |

## Integrations

- **Traefik**: Firefly III at `firefly.{{ domainname_infra }}`, importer at `firefly-importer.{{ domainname_infra }}`, both with Let's Encrypt TLS.
- **N26 import config**: A pre-built import configuration for N26 CSV exports is included at `files/n26_firefly_import_config.json`. You can load it directly in the importer UI.
