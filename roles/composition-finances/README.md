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
| `firefly_cron_token` | Token for the Firefly III cron endpoint |
| `firefly_db_password` | MariaDB password |
| `firefly_app_key` | Laravel application encryption key (32 chars) |

All three must be set (they default to `null`); store them in Ansible Vault.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/firefly-upload` | User-uploaded attachments |
| `{{ composition_config }}/firefly-db` | MariaDB data directory |

## Integrations

- **Traefik**: Firefly III at `firefly.{{ domain_name }}`, importer at `firefly-importer.{{ domain_name }}`, both with Let's Encrypt TLS.
- **N26 import config**: A pre-built import configuration for N26 CSV exports is included at `files/n26_firefly_import_config.json` and can be loaded directly in the importer UI.
