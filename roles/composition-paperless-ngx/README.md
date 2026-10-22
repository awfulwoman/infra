# Paperless-ngx

Document management with full-text search, OCR, and (optionally) automatic
translation of non-English documents into English on ingest.

## Services

| Service | Purpose |
|---------|---------|
| `webserver` | Paperless-ngx (UI + consumer worker) |
| `db` | Postgres 16 |
| `broker` | Redis 8 (paperless celery) |
| `gotenberg` | Office/PDF conversion |
| `tika` | Text extraction |

## Auto-translation

[`composition-translation-server`](../composition-translation-server/README.md)
translates new German documents into linked English companions. Paperless
calls its connector through the **Translate to English** workflow (webhook
action), which that role creates through the API. Nothing in this role
takes part.

## DNS

Registers subdomain: `paperless`

## Vault entries (per host)

| Variable | Purpose |
|----------|---------|
| `vault_paperless_ngx_db_password` | Postgres password |
| `vault_paperless_ngx_secret_key` | Django secret key |
| `vault_paperless_ngx_admin_password` | Initial admin password |
| `vault_paperless_ngx_admin_mail` | Initial admin email |
| `vault_paperless_ngx_api_token` | Paperless REST API token (admin); also used by composition-translation-server |
