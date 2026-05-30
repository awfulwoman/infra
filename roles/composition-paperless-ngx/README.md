# Paperless-ngx

Document management with full-text search, OCR, and (optionally) automatic
translation of non-English documents into English on ingest.

## Services

| Service | Purpose |
|---------|---------|
| `webserver` | Paperless-ngx (UI + consumer worker) |
| `db` | Postgres 16 |
| `broker` | Redis 8 (paperless celery on DB 0; translator queue on DB 1) |
| `gotenberg` | Office/PDF conversion |
| `tika` | Text extraction |
| `translator` | Auto-translation sidecar (optional, see below) |

## Auto-translation

When `paperless_ngx_translate_enabled` is `true` (default), a custom `translator`
service is built and run. It reuses the existing
[`composition-libretranslate`](../composition-libretranslate/README.md) instance
on the same host via the shared `default_docker_network`.

On each consumed document, paperless invokes the post-consume hook (a small
shell script mounted read-only into the webserver) which fires a fire-and-forget
POST to the translator. The translator enqueues the job onto Redis DB 1, a single
worker thread picks it up, detects the language via LibreTranslate, applies OCR
cleanup, translates non-English content in chunks, and POSTs the result back to
paperless as a Note prefixed `**Auto-translation`.

The original OCR `content` field is never modified.

### Manual triggers

The translator exposes these internal HTTP endpoints (not Traefik-fronted):

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/translate` | Body `{"document_id": N}` — enqueue a translation |
| `GET`  | `/status`    | Queue + counter snapshot |
| `GET`  | `/healthz`   | Redis + LibreTranslate + paperless reachability |

From the host:

```bash
docker exec paperless_translator curl -fsS http://localhost:5000/status
```

### Kill switch

Set `paperless_ngx_translate_enabled: false` to remove the translator service from
compose, drop the post-consume env var, and skip rendering the translator build
context. Paperless continues to operate normally.

## DNS

Registers subdomain: `paperless`

## Vault entries (per host)

| Variable | Purpose |
|----------|---------|
| `vault_paperless_ngx_db_password` | Postgres password |
| `vault_paperless_ngx_secret_key` | Django secret key |
| `vault_paperless_ngx_admin_password` | Initial admin password |
| `vault_paperless_ngx_admin_mail` | Initial admin email |
| `vault_paperless_ngx_libretranslate_api_key` | LibreTranslate API key (required when translation enabled) |
| `vault_paperless_ngx_api_token` | Paperless REST API token (required when translation enabled) |
