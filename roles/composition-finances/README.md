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
| `firefly_mail_mailer` | `log` — no SMTP relay is wired in, mail goes to the container log |
| `firefly_log_level` | `notice` normally; must be `debug` to recover a reset link |

The three vault variables must be set (they default to `null`); store them in
Ansible Vault.

## Recovering a lost password

Firefly III enforces a 16-character minimum password and
[the minimum cannot be lowered](https://docs.firefly-iii.org/references/faq/firefly-iii/using/).
There is no artisan command to set a password, so recovery goes through the
normal reset flow — which needs mail. `MAIL_MAILER=log` writes the reset mail
to the container log instead of sending it, but Firefly logs mail at debug
level, so `APP_LOG_LEVEL` has to be raised for the duration.

```bash
# 1. Redeploy with debug logging on
ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml \
  --tags composition -e target_composition=finances -e firefly_log_level=debug

# 2. Request a reset at https://firefly.<domain>/password/reset

# 3. Read the link out of the log
ssh server-64gb-storage \
  'docker logs --since 5m firefly_iii_core 2>&1 | grep -oE "https://[^ \"<>]*password/reset/[A-Za-z0-9]+" | tail -1'

# 4. Set a password of at least 16 characters, then redeploy without the
#    -e override to drop the log level back to notice
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
