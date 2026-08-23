# Finances

Deploys [Firefly III](https://www.firefly-iii.org/), a self-hosted personal finance manager, along with its data importer for ingesting bank exports. Firefly III tracks income, expenses, budgets, and categories across multiple accounts.

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

The three vault variables must be set (they default to `null`); store them in
Ansible Vault.

## Enable Banking

The data importer talks to [Enable Banking](https://enablebanking.com/) using an
application ID and a private key, following the
[upstream tutorial](https://docs.firefly-iii.org/tutorials/data-importer/eb/).

These credentials reach live bank data, so — unlike the rest of this role's
secrets — they are **not** kept in the repo, not even Ansible Vault. They live
only in 1Password (item `fisnhyavlrcztjznla55kuzdu4`, fields `App ID` and
`Private Key`) and are fetched through 1Password Connect each time the role
runs, then written straight into `.environment_vars_importer` on the host. The
fetch is delegated to the controller so the Connect token never reaches the
target.

The private key is stored in 1Password as an **ordinary multi-line PEM** — the
`.pem` file's contents pasted in verbatim, real line breaks and all. The role
passes it through untouched.

The upstream tutorial instead shows the key collapsed onto one line with literal
`\n` escapes. That is what you need when the value lands in Laravel's own `.env`
and phpdotenv expands the escapes, but it is the wrong form here: this
composition delivers the value through Docker Compose `env_file`, which does no
escape expansion, so openssl would receive two literal characters where a line
break belongs. Compose does preserve real newlines in a quoted `env_file` value
(verified on the Compose v5.5.0 running on storage), so the plain PEM needs no
conversion at all.

The item must live in the `Infra` vault, since that is the only vault the
Connect read token can see. Note that 1Password reassigns an item's UUID when
it moves between vaults, so `firefly_enablebanking_item_id` must be updated if
the item is ever relocated. Confirm it is visible and correctly shaped with:

```bash
ansible-playbook playbooks/utility/check-enablebanking-credentials.yaml
```

Neither `ENABLE_BANKING_IMPORT_IP_HEADER` nor `ENABLE_BANKING_IMPORT_IP` is set
here, and neither needs to be. They control the PSD2 `PSU-IP-Address` header,
which carries the end user's real IP for strong customer authentication. The
importer only reads the IP when the header flag is `true`, and it defaults to
`false`, so the header is simply never sent. Set both only if a bank
specifically demands it — and note that the `autodetect` value calls out to
icanhazip.com, and that a private address such as the `127.0.0.1` default fails
the importer's own public-IP validation and is dropped.

## Recovering a lost password

Firefly III enforces a 16-character minimum password and
[the minimum cannot be lowered](https://docs.firefly-iii.org/references/faq/firefly-iii/using/).
There is no artisan command to set a password, so the reset flow at
`https://firefly.<domain>/password/reset` is the only recovery path — hence
the SMTP config above. Any replacement password must be at least 16
characters or the reset form will reject it.

If SMTP itself is broken, fall back to the log mailer: Firefly writes the
mail to the container log instead of sending it, but only at debug level.

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

If the reset form refuses to issue a new token, clear stale rows first:
`DELETE FROM password_resets;` in the `firefly` database.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/firefly-upload` | User-uploaded attachments |
| `{{ composition_config }}/firefly-db` | MariaDB data directory |

## Integrations

- **Traefik**: Firefly III at `firefly.{{ domainname_infra }}`, importer at `firefly-importer.{{ domainname_infra }}`, both with Let's Encrypt TLS.
- **N26 import config**: A pre-built import configuration for N26 CSV exports is included at `files/n26_firefly_import_config.json` and can be loaded directly in the importer UI.
