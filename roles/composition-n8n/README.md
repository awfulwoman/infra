# composition-n8n

Deploys [n8n](https://github.com/n8n-io/n8n) — a workflow automation tool.

## Required vars (vault-encrypted)

| Variable | Description |
|---|---|
| `n8n_db_password` | PostgreSQL password for the n8n user |
| `n8n_encryption_key` | n8n encryption key for credentials at rest |
