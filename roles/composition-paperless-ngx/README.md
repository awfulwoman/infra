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
| `pdf-translate-webhook` | Auto-translation sidecar (optional, see below) |

## Auto-translation

When `paperless_ngx_translate_enabled` is `true` (default), the role runs the
[pdf-translate Paperless webhook](https://github.com/jctots/pdf-translate/tree/main/paperless_webhook)
as `pdf-translate-webhook`. It uses
[`composition-pdf-translate`](../composition-pdf-translate/README.md) and
[`composition-libretranslate`](../composition-libretranslate/README.md) on the
same host through the shared `default_docker_network`.

On each consumed document, paperless runs the post-consume hook (a small shell
script mounted read-only into the webserver). The hook sends
`{"document_id": N}` to the webhook and does not wait. The webhook then:

1. Detects the language with LibreTranslate. Documents that are not
   `paperless_ngx_translate_source_lang` (`de`) are skipped.
2. Sends the PDF to pdf-translate, which translates with Ollama on Malcolm
   (`translategemma:4b`).
3. Uploads the translated PDF as a new document titled `[EN] <title>`, tagged
   `auto-translated`.
4. Links the original and the companion through the `translation` custom field
   (Document Link). The role creates this field through the API.

On failure the original gets the `translation-failed` tag. To retry,
run the backfill for that ID (see below). The original is never changed.

`files/pdf-translate-webhook/sitecustomize.py` patches the webhook (0.2.1) for
the Paperless 3.x tasks API. Without it, companions upload but are never
linked (`uploaded_unlinked`). Remove it when upstream supports 3.x.

We use the post-consume hook, not a Paperless Workflow, so nothing is set up by
hand in the UI.

Log: `config/pdf-translate-webhook/translate.log` (one JSON line per document).

### Backfill existing documents

```bash
docker exec -it pdf-translate-webhook python backfill.py --start 1 --end 50 --dry-run
docker exec -it pdf-translate-webhook python backfill.py --start 1 --end 50
```

### Kill switch

Set `paperless_ngx_translate_enabled: false` to turn off translation. This
removes the webhook service from compose and drops the post-consume
environment variable. Paperless continues to work normally.

### History

This replaced a custom `translator` sidecar that added LibreTranslate text as a
note. Existing `**Auto-translation` notes stay on their documents.

## DNS

Registers subdomain: `paperless`

## Vault entries (per host)

| Variable | Purpose |
|----------|---------|
| `vault_paperless_ngx_db_password` | Postgres password |
| `vault_paperless_ngx_secret_key` | Django secret key |
| `vault_paperless_ngx_admin_password` | Initial admin password |
| `vault_paperless_ngx_admin_mail` | Initial admin email |
| `vault_paperless_ngx_api_token` | Paperless REST API token (required when translation enabled) |
