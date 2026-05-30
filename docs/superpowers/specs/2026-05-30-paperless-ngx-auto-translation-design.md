# Paperless-ngx Auto-Translation

**Date:** 2026-05-30
**Status:** Approved

## Problem

Documents ingested into paperless-ngx on `server-64gb-storage` include foreign-language items (primarily German). Their OCR text stays in the source language, which hurts discoverability when searching in English and forces manual look-ups for routine paperwork.

The user wants new documents to be translated automatically into English on ingest, with the translation stored on the document in a way that does not damage the original OCR content.

Inspiration: <https://github.com/charlesvestal/paperless-translate>, which appends translations to the document's Content field using LibreTranslate plus a small Flask queue.

## Goals

1. Translate every newly-consumed paperless document into English automatically.
2. Detect source language at runtime — no per-doc configuration required.
3. Preserve the original OCR text untouched; expose the translation alongside it.
4. Reuse the existing `composition-libretranslate` role on the same host rather than running a second LibreTranslate instance.
5. Survive translator/LibreTranslate restarts without dropping in-flight jobs.
6. Provide a kill switch so the feature can be disabled without removing code.

## Non-Goals

- A web UI for managing the translation queue. The JSON `/status` endpoint suffices.
- Bulk re-translation of existing documents in the paperless library.
- Translation to languages other than English.
- Modifying `composition-libretranslate` (e.g. setting `LT_LOAD_ONLY`). That role remains untouched.
- A metrics endpoint (Prometheus/VictoriaMetrics). Logs to Loki are enough for now.

## Architecture Overview

```
┌────────────────────────────┐         ┌──────────────────────────┐
│ composition-paperless-ngx  │         │ composition-libretranslate│
│                            │         │                          │
│ webserver ──POST_CONSUME──▶│ translat│  libretranslate (5000,   │
│    ▲      doc_id            │   or   │──▶ API-key-protected)    │
│    │ paperless REST API     │ (Flask │ │                          │
│    └──notes/───────────────│  +     │ └──────────────────────────┘
│                             │ worker)│
│ broker (redis) ◀──enqueue──│        │   shared default_docker_network
│                ──dequeue───▶│        │
└────────────────────────────┘
```

Two pieces:

- A new **`translator`** service inside `composition-paperless-ngx`. Custom-built Python image (Flask + worker thread). Provides `/translate`, `/status`, `/healthz`.
- A new **post-consume shell script** wired into the existing paperless webserver via `PAPERLESS_POST_CONSUME_SCRIPT`.

The translator uses the **existing** redis broker (already running for paperless's celery) as a job queue. It calls the **existing** `composition-libretranslate` over the shared `default_docker_network` (container name `libretranslate`).

`composition-libretranslate` has `LT_API_KEYS=true`, so the translator needs an API key, stored in vault.

## Component Detail

### Files added under `roles/composition-paperless-ngx/`

```
templates/
  scripts/
    post_consume.sh.j2           NEW: 1-screen shell hook
  translator/
    Dockerfile.j2                NEW: build context
    requirements.txt.j2          NEW: pinned Python deps
    app.py.j2                    NEW: Flask + worker thread
    ocr_cleanup.py.j2            NEW: regex cleanup ported from reference repo
  docker-compose.yaml.j2         MODIFIED: add translator service + script mount + POST_CONSUME env
tasks/
  main.yaml                      MODIFIED: create scripts/translator dirs + render new files
defaults/
  main.yaml                      MODIFIED: new translate_* vars
README.md                        NEW: brief role doc
```

### New default vars (`defaults/main.yaml`)

```yaml
paperless_ngx_translate_enabled: true
paperless_ngx_translate_libretranslate_url: "http://libretranslate:5000"
paperless_ngx_translate_libretranslate_api_key: "{{ vault_paperless_ngx_libretranslate_api_key }}"
paperless_ngx_translate_target_lang: "en"
paperless_ngx_translate_skip_source_langs:
  - en
paperless_ngx_translate_min_confidence: 0.5
paperless_ngx_translate_chunk_size: 4000
paperless_ngx_translate_ocr_cleanup_enabled: true
paperless_ngx_api_token: "{{ vault_paperless_ngx_api_token }}"
```

Setting `paperless_ngx_translate_enabled: false` omits the translator service and the `PAPERLESS_POST_CONSUME_SCRIPT` env line entirely.

### New vault entries

Added to `inventory/host_vars/server-64gb-storage/vault_paperless_ngx.yaml`:

- `vault_paperless_ngx_libretranslate_api_key` — issued via `docker exec libretranslate ./venv/bin/ltmanage keys add <daily-limit> paperless-ngx`.
- `vault_paperless_ngx_api_token` — generated in the paperless UI under My Profile → Auth tokens.

Both encrypted with `ansible-vault encrypt_string … --name '<var>'` per `.claude/rules/ansible-vault.md`.

### Translator service (compose)

```yaml
translator:
  container_name: paperless_translator
  build:
    context: ./translator
  restart: unless-stopped
  env_file: .environment_vars_translator
  depends_on:
    broker:
      condition: service_healthy
  networks:
    - "{{ default_docker_network }}"
  healthcheck:
    test: ["CMD", "curl", "-fs", "http://localhost:5000/healthz"]
    interval: 30s
    timeout: 5s
    retries: 3
```

No Traefik labels — internal-only. Custom-built image, no `pip install` at container start.

### Webserver changes

- New env line: `PAPERLESS_POST_CONSUME_SCRIPT=/usr/src/paperless/scripts/post_consume.sh`
- New read-only volume: `{{ composition_config }}/scripts:/usr/src/paperless/scripts:ro`
- `depends_on` gains `translator: { condition: service_started }` (not `service_healthy` — translator outage must not block paperless startup).

### Translator env file (`.environment_vars_translator`)

```
PAPERLESS_URL=http://webserver:8000
PAPERLESS_API_TOKEN={{ paperless_ngx_api_token }}
LIBRETRANSLATE_URL={{ paperless_ngx_translate_libretranslate_url }}
LIBRETRANSLATE_API_KEY={{ paperless_ngx_translate_libretranslate_api_key }}
REDIS_URL=redis://broker:6379/1
TARGET_LANG={{ paperless_ngx_translate_target_lang }}
SKIP_SOURCE_LANGS={{ paperless_ngx_translate_skip_source_langs | join(',') }}
MIN_CONFIDENCE={{ paperless_ngx_translate_min_confidence }}
CHUNK_SIZE={{ paperless_ngx_translate_chunk_size }}
OCR_CLEANUP_ENABLED={{ paperless_ngx_translate_ocr_cleanup_enabled | string | lower }}
```

Redis DB index `1` is used (paperless uses index `0`) to keep the queue isolated.

## Data Flow

```
1. User uploads doc → paperless ingests it
2. paperless invokes PAPERLESS_POST_CONSUME_SCRIPT with DOCUMENT_ID env
3. post_consume.sh:
     curl --max-time 5 -fsS -X POST http://translator:5000/translate \
       -H "Content-Type: application/json" \
       -d "{\"document_id\": ${DOCUMENT_ID}}" || true
   # exits 0 unconditionally — paperless never fails ingestion on translator outage
4. translator HTTP handler /translate:
     - validates payload
     - reads existing notes; if a note starts with "**Auto-translation",
       returns 200 {"already_processed": true}
     - LPUSH "paperless-translate:queue" <doc_id> on redis
     - returns 202 {"queued": true}
5. translator worker thread (single consumer):
     a. BRPOP "paperless-translate:queue"
     b. Re-check notes for idempotency
     c. GET /api/documents/{id}/ → fetch `content`
     d. If OCR_CLEANUP_ENABLED: apply regex cleanup
     e. POST /detect on libretranslate (with API key)
     f. If source ∈ SKIP_SOURCE_LANGS or confidence < MIN_CONFIDENCE:
          POST a skip note, increment completed, done
     g. Chunk content by CHUNK_SIZE, POST /translate per chunk
     h. Concatenate translated chunks
     i. POST /api/documents/{id}/notes/ with translation
     j. Increment completed counter
```

## HTTP Contracts

### Translator → external callers

| Method | Path        | Body                       | Response |
|--------|-------------|----------------------------|----------|
| POST   | `/translate`| `{"document_id": int}`     | `202 {"queued": true}` / `200 {"already_processed": true}` / `400` |
| GET    | `/status`   | —                          | `200 {"queued": N, "in_flight": 0|1, "completed": N, "failed": N}` |
| GET    | `/healthz`  | —                          | `200` if redis + libretranslate + paperless all reachable, else `503` |

### Translator → paperless (Token auth, internal URL)

- `GET  http://webserver:8000/api/documents/{id}/`
- `POST http://webserver:8000/api/documents/{id}/notes/` body `{"note": "<rendered>"}`

Header: `Authorization: Token {{ paperless_ngx_api_token }}`.

### Translator → libretranslate

- `POST /detect`   body `{"q": "<first 2000 chars>", "api_key": "<key>"}`
- `POST /translate` body `{"q": "<chunk>", "source": "<detected>", "target": "en", "format": "text", "api_key": "<key>"}`

## Note Format

```markdown
**Auto-translation (de → en, LibreTranslate)**
_Generated 2026-05-30 14:22 UTC_

<translated text>
```

Skip / failure variants follow the same prefix convention:

- `**Auto-translation skipped (source: en)**`
- `**Auto-translation skipped (low confidence)**`
- `**Auto-translation skipped (unsupported source: xx)**`
- `**Auto-translation skipped (empty content)**`
- `**Auto-translation FAILED**` — followed by reason

The leading `**Auto-translation` prefix is the idempotency marker.

## Error Handling

| Failure                                            | Behaviour                                                                                          |
|----------------------------------------------------|----------------------------------------------------------------------------------------------------|
| Post-consume can't reach translator                | `curl … || true`, exit 0. Manual re-trigger possible via `curl -X POST /translate -d '{"document_id":N}'`. |
| Bad doc_id (deleted before dequeue)                | Warn, mark failed, move on.                                                                        |
| Paperless API 5xx / network blip                   | Exponential backoff 1→2→4→8→16s, then re-LPUSH job tail, increment retry counter.                  |
| LibreTranslate down / 5xx                          | Same backoff. After 5 retries, mark failed and post FAILED note with reason.                       |
| LibreTranslate 400 (unsupported lang pair)         | Don't retry. Post skip note with source language.                                                  |
| Detection confidence < `MIN_CONFIDENCE`            | Skip + post low-confidence note. No retry.                                                         |
| `len(content.strip()) < 20`                        | Skip + post empty-content note.                                                                    |
| Note POST permanently fails                        | Mark failed. Translation remains in log; manual re-trigger redoes it.                              |

Single-consumer worker (one in-flight job at a time) keeps memory and LibreTranslate load predictable; avoids concurrency primitives.

## Idempotency

Two layers, both based on the `**Auto-translation` prefix on existing notes:

1. **Pre-enqueue** — `/translate` handler returns `already_processed` without enqueueing.
2. **Post-dequeue** — worker re-checks notes immediately before posting, in case a duplicate enqueue raced through.

Force re-translate = delete the note in the paperless UI, POST again.

## Observability

| Surface           | Content                                                                                  |
|-------------------|------------------------------------------------------------------------------------------|
| Container stdout  | Structured JSON-ish lines (`ts`, `doc`, `event`, `lang`, `conf`, `error`). Picked up by the existing Loki composition on this host. |
| `/status`         | Counters: queued, in_flight (0/1), completed_total, failed_total                          |
| `/healthz`        | 200 only when redis ping + LibreTranslate `/languages` + paperless `/api/` all succeed    |
| Compose healthcheck | `curl -fs http://localhost:5000/healthz` — surfaces in `docker ps` and container-management UI |

## Testing

The repo does not run a unit-test harness in CI. Verification is a checklist:

**Pre-deploy (local smoke)**
1. Build the translator image locally; stand it up with env pointing at libretranslate via Tailscale.
2. `curl -X POST localhost:5000/translate -d '{"document_id": <known German doc>}'` → note appears in paperless UI within ~30s.
3. Re-POST same doc → response `already_processed`, no second note.
4. POST a known English doc → skip note appears.
5. POST a doc whose content > 2× `CHUNK_SIZE` → translation reads coherently end-to-end.
6. Stop libretranslate → POST a doc → observe backoff in logs → restart libretranslate → job drains.

**Post-deploy on `server-64gb-storage`**
1. `docker compose ps` shows translator `(healthy)`.
2. `docker compose logs translator --tail 50` clean startup, `/healthz` green.
3. Ingest one German doc via paperless UI; observe Note within ~30s.

## Boundaries Honoured

- `composition-libretranslate` — not modified.
- `composition-common` — not modified.
- `playbooks/hosts/server-64gb-storage/core.yaml` — not modified (libretranslate already comes before paperless-ngx).
- `network-register-subdomain` — no new subdomain.

## Future Work (out of scope here)

- Re-translate-historical-docs one-shot script.
- Multi-target translation.
- Prometheus/VictoriaMetrics metrics endpoint.
- Per-document opt-out via tag (e.g. `no-translate`).
