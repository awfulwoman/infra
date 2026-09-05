# Paperless-ngx

Document management with full-text search, OCR, and (optionally) automatic
translation of non-English documents into English on ingest.

## Services

| Service | Purpose |
|---------|---------|
| `webserver` | Paperless-ngx (UI + consumer worker) |
| `db` | Postgres 16 |
| `broker` | Redis 8 (paperless celery on DB 0, translator queue on DB 1) |
| `gotenberg` | Office/PDF conversion |
| `tika` | Text extraction |
| `translator` | Auto-translation sidecar (optional, see below) |

## Auto-translation

When `paperless_ngx_translate_enabled` is `true` (default), the role builds and
runs a custom `translator` service. It reuses the existing
[`composition-libretranslate`](../composition-libretranslate/README.md) instance
on the same host through the shared `default_docker_network`.

On each consumed document, paperless invokes the post-consume hook (a small
shell script mounted read-only into the webserver), which fires a fire-and-forget
POST to the translator. When the translator receives the job, it does the following:

1. Adds the job to the queue on Redis DB 1.
2. Picks it up with a single worker thread.
3. Detects the language with LibreTranslate.
4. Applies OCR cleanup.
5. Translates non-English content in chunks.
6. Posts the result back to paperless as a note with the prefix `**Auto-translation`.

The translator never changes the original OCR `content` field.

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

Set `paperless_ngx_translate_enabled: false` to turn off the translator. This
removes the translator service from compose, drops the post-consume environment
variable, and skips the translator build step. Paperless continues to work
normally.

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
