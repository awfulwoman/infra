# Paperless-ngx Auto-Translation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `roles/composition-paperless-ngx` so that newly-consumed documents are automatically translated into English (when not already English) via the existing `composition-libretranslate` service on the same host, with the translation written back as a paperless Note.

**Architecture:** A new Python `translator` sidecar service is added to `composition-paperless-ngx`. Paperless's `PAPERLESS_POST_CONSUME_SCRIPT` fires a fire-and-forget HTTP call to the translator on each ingest. The translator enqueues the job onto the existing redis broker (separate DB index), and a single worker thread dequeues, detects language via LibreTranslate, chunks long content, translates, and POSTs a Note to paperless's API. All cross-service traffic is internal-only over `default_docker_network`.

**Tech Stack:** Ansible (Jinja2 templates), Python 3.12 (Flask, redis-py, requests), Docker Compose, LibreTranslate, paperless-ngx REST API.

**Spec:** `docs/superpowers/specs/2026-05-30-paperless-ngx-auto-translation-design.md`

**Conventions to honour:**
- Project `.claude/rules/ansible-vault.md` — inline secret-generation commands
- Project `.claude/rules/python.md` — no venv at repo root; Python is brewed
- Project `.claude/rules/precommit.md` — `pre-commit` runs on every commit
- Project `.claude/rules/ansible-facts.md` — access facts via `ansible_facts['…']`, never bare `ansible_machine`
- Pre-commit hooks: `check-yaml` (excludes `roles/*/templates/*.yaml`), `end-of-file-fixer`, `trailing-whitespace`, `detect-private-key`, `check-added-large-files`

---

## File Structure

### New files

```
roles/composition-paperless-ngx/
  README.md                                            ← NEW
  templates/
    scripts/
      post_consume.sh.j2                               ← NEW
    translator/
      Dockerfile.j2                                    ← NEW
      requirements.txt.j2                              ← NEW
      app.py.j2                                        ← NEW (Flask app + worker thread)
      ocr_cleanup.py.j2                                ← NEW (pure regex transforms)
      test_translator.py.j2                            ← NEW (pytest unit tests; run at image build)
docs/superpowers/plans/
  2026-05-30-paperless-ngx-auto-translation.md         ← this file (already created)
```

### Modified files

```
roles/composition-paperless-ngx/
  defaults/main.yaml                                   ← MODIFIED (add translate_* vars)
  tasks/main.yaml                                      ← MODIFIED (render new files, new dirs)
  templates/docker-compose.yaml.j2                     ← MODIFIED (add translator service, post-consume wiring on webserver)
inventory/host_vars/server-64gb-storage/
  vault_paperless_ngx.yaml                             ← MODIFIED (add 2 vault vars)
```

### Responsibilities

| File | Responsibility |
|---|---|
| `defaults/main.yaml` | Defaults for `paperless_ngx_translate_*` vars, including the kill switch |
| `tasks/main.yaml` | Create new dirs, render new templates, gate on `paperless_ngx_translate_enabled` |
| `templates/docker-compose.yaml.j2` | Add `translator` service; mount scripts into webserver; add `PAPERLESS_POST_CONSUME_SCRIPT` env; declare new dep |
| `templates/scripts/post_consume.sh.j2` | One curl call; fire-and-forget; exits 0 unconditionally |
| `templates/translator/Dockerfile.j2` | Build a slim Python 3.12 image with pinned deps; run pytest at build to fail fast |
| `templates/translator/requirements.txt.j2` | Pinned Python deps |
| `templates/translator/app.py.j2` | Flask routes, single-consumer worker thread, paperless+LT clients (inline) |
| `templates/translator/ocr_cleanup.py.j2` | Pure regex transforms — easy to unit-test |
| `templates/translator/test_translator.py.j2` | Pytest cases for OCR cleanup + chunking; runs in Docker build |
| `vault_paperless_ngx.yaml` | Two new vault secrets: LibreTranslate API key, paperless API token |

---

## Task 1: Generate and add vault secrets

**Files:**
- Modify: `inventory/host_vars/server-64gb-storage/vault_paperless_ngx.yaml`

**Why first:** Every downstream task references these vars. Generate the values once, encrypt, paste, move on.

- [ ] **Step 1: SSH to server and create a LibreTranslate API key for paperless**

Run (on your workstation):

```bash
ssh server-storage 'docker exec libretranslate ./venv/bin/ltmanage keys add 1000 paperless-ngx'
```

Expected output: a long hex string (the key). Copy it.

If `ltmanage` is not on PATH, the alternative is:

```bash
ssh server-storage 'docker exec libretranslate sh -c "cd /app && ./venv/bin/python -m libretranslate.manage keys add 1000 paperless-ngx"'
```

- [ ] **Step 2: Generate a paperless API token in the UI**

Open `https://paperless.{{ domainname_infra }}` → My Profile → Auth Tokens → Generate. Copy the token.

- [ ] **Step 3: Encrypt both values**

```bash
ansible-vault encrypt_string "<LT-KEY-FROM-STEP-1>" --name 'vault_paperless_ngx_libretranslate_api_key'
ansible-vault encrypt_string "<PAPERLESS-TOKEN-FROM-STEP-2>" --name 'vault_paperless_ngx_api_token'
```

- [ ] **Step 4: Append both encrypted strings to the vault file**

Open `inventory/host_vars/server-64gb-storage/vault_paperless_ngx.yaml` and append the two new vars at the end of the file. Result should resemble:

```yaml
# existing entries unchanged …

vault_paperless_ngx_libretranslate_api_key: !vault |
  $ANSIBLE_VAULT;1.2;AES256;beanpod
  <ciphertext>
vault_paperless_ngx_api_token: !vault |
  $ANSIBLE_VAULT;1.2;AES256;beanpod
  <ciphertext>
```

- [ ] **Step 5: Verify the file decrypts cleanly**

```bash
ansible-vault view inventory/host_vars/server-64gb-storage/vault_paperless_ngx.yaml
```

Expected: full YAML printed without error; the new keys are present and look like non-empty strings.

- [ ] **Step 6: Commit**

```bash
git add inventory/host_vars/server-64gb-storage/vault_paperless_ngx.yaml
git commit -m "feat(vault): add paperless-ngx translation secrets"
```

---

## Task 2: Add new defaults to the role

**Files:**
- Modify: `roles/composition-paperless-ngx/defaults/main.yaml`

- [ ] **Step 1: Append the new vars to defaults/main.yaml**

After the existing `paperless_ngx_admin_mail` line, append:

```yaml

# ----------------------------
# Auto-translation
# ----------------------------

paperless_ngx_translate_enabled: true
# URL of an existing LibreTranslate instance reachable on the default Docker network.
paperless_ngx_translate_libretranslate_url: "http://libretranslate:5000"
paperless_ngx_translate_libretranslate_api_key: "{{ vault_paperless_ngx_libretranslate_api_key }}"
paperless_ngx_translate_target_lang: "en"
# When the detected source language matches any of these, translation is skipped.
paperless_ngx_translate_skip_source_langs:
  - en
# Detection confidence below which translation is skipped (LibreTranslate returns 0-100).
paperless_ngx_translate_min_confidence: 50
# Max characters per /translate request. LibreTranslate's default char-limit is 5000.
paperless_ngx_translate_chunk_size: 4000
paperless_ngx_translate_ocr_cleanup_enabled: true
# Paperless REST API token used by the translator to read documents and POST notes.
paperless_ngx_api_token: "{{ vault_paperless_ngx_api_token }}"
```

- [ ] **Step 2: Syntax check**

```bash
ansible-playbook --syntax-check playbooks/hosts/server-64gb-storage/core.yaml
```

Expected: `playbook: playbooks/hosts/server-64gb-storage/core.yaml` (no errors).

- [ ] **Step 3: Commit**

```bash
git add roles/composition-paperless-ngx/defaults/main.yaml
git commit -m "feat(composition-paperless-ngx): add translation defaults"
```

---

## Task 3: Pin Python dependencies for the translator

**Files:**
- Create: `roles/composition-paperless-ngx/templates/translator/requirements.txt.j2`

- [ ] **Step 1: Create the directory**

```bash
mkdir -p roles/composition-paperless-ngx/templates/translator
mkdir -p roles/composition-paperless-ngx/templates/scripts
```

- [ ] **Step 2: Write the requirements file**

Create `roles/composition-paperless-ngx/templates/translator/requirements.txt.j2`:

```
flask==3.0.3
gunicorn==22.0.0
redis==5.0.7
requests==2.32.3
pytest==8.3.2
```

(No Jinja interpolation needed today, but the `.j2` extension keeps the door open for templated pinning later.)

- [ ] **Step 3: Commit**

```bash
git add roles/composition-paperless-ngx/templates/translator/requirements.txt.j2
git commit -m "feat(composition-paperless-ngx): pin translator deps"
```

---

## Task 4: Write the OCR cleanup module (pure functions, easy to test)

**Files:**
- Create: `roles/composition-paperless-ngx/templates/translator/ocr_cleanup.py.j2`

**Why:** Scanned German documents commonly have OCR artefacts (hyphenated line breaks, smart-quote noise, repeated spaces). Cleaning before translation noticeably improves output quality. These are pure functions so they are trivial to unit-test.

- [ ] **Step 1: Create the file**

Path: `roles/composition-paperless-ngx/templates/translator/ocr_cleanup.py.j2`

```python
"""OCR cleanup transforms applied before translation.

Pure functions; deterministic; no I/O.
"""
from __future__ import annotations

import re

_HYPHEN_LINEBREAK = re.compile(r"(\w+)-\n(\w+)")
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_TRAILING_WS_PER_LINE = re.compile(r"[ \t]+\n")
_SMART_QUOTES = {
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
    "–": "-",
    "—": "-",
}


def fix_hyphen_linebreaks(text: str) -> str:
    """Join word-fragments split across a hyphenated line break."""
    return _HYPHEN_LINEBREAK.sub(r"\1\2", text)


def collapse_whitespace(text: str) -> str:
    text = _TRAILING_WS_PER_LINE.sub("\n", text)
    text = _MULTI_SPACE.sub(" ", text)
    text = _MULTI_NEWLINE.sub("\n\n", text)
    return text


def normalise_quotes(text: str) -> str:
    for src, dst in _SMART_QUOTES.items():
        text = text.replace(src, dst)
    return text


def clean(text: str) -> str:
    """Apply all cleanup steps in order."""
    text = fix_hyphen_linebreaks(text)
    text = normalise_quotes(text)
    text = collapse_whitespace(text)
    return text.strip()
```

- [ ] **Step 2: Commit**

```bash
git add roles/composition-paperless-ngx/templates/translator/ocr_cleanup.py.j2
git commit -m "feat(composition-paperless-ngx): add OCR cleanup module"
```

---

## Task 5: Write the test module

**Files:**
- Create: `roles/composition-paperless-ngx/templates/translator/test_translator.py.j2`

**Why:** Pure-function tests for OCR cleanup and chunking. Runs once at Docker build (`RUN pytest -q`) so a regression here fails the deploy instead of the translation pipeline.

- [ ] **Step 1: Create the test file**

Path: `roles/composition-paperless-ngx/templates/translator/test_translator.py.j2`

```python
"""Unit tests for translator pure functions.

Run via `pytest -q` inside the translator image during Docker build.
"""
from __future__ import annotations

import ocr_cleanup
from app import chunk_text


def test_hyphen_linebreak_joined():
    src = "Versiche-\nrungsschein"
    assert ocr_cleanup.fix_hyphen_linebreaks(src) == "Versicherungsschein"


def test_smart_quotes_normalised():
    src = "“Hallo” — sagte er"
    assert ocr_cleanup.normalise_quotes(src) == '"Hallo" - sagte er'


def test_whitespace_collapsed():
    src = "ein    Text  \nmit \n\n\n\nlücken"
    out = ocr_cleanup.collapse_whitespace(src)
    assert "    " not in out
    assert "\n\n\n" not in out


def test_clean_idempotent():
    src = "Versiche-\nrungs-  schein  "
    once = ocr_cleanup.clean(src)
    twice = ocr_cleanup.clean(once)
    assert once == twice


def test_chunk_small_text_single_chunk():
    chunks = list(chunk_text("hello world", chunk_size=100))
    assert chunks == ["hello world"]


def test_chunk_splits_on_paragraph_when_possible():
    text = "para one.\n\n" + ("x" * 50) + "\n\npara three."
    chunks = list(chunk_text(text, chunk_size=60))
    # Each chunk is under the budget, no chunk is empty, and concatenation preserves content.
    assert all(0 < len(c) <= 60 for c in chunks)
    assert "para one." in chunks[0]
    assert "para three." in chunks[-1]


def test_chunk_hard_splits_when_no_breakpoint():
    text = "x" * 10_000
    chunks = list(chunk_text(text, chunk_size=4000))
    assert all(len(c) <= 4000 for c in chunks)
    assert "".join(chunks) == text
```

- [ ] **Step 2: Commit**

```bash
git add roles/composition-paperless-ngx/templates/translator/test_translator.py.j2
git commit -m "test(composition-paperless-ngx): add translator unit tests"
```

---

## Task 6: Write the Flask app + worker

**Files:**
- Create: `roles/composition-paperless-ngx/templates/translator/app.py.j2`

**Why:** Single source file for the service. Roughly 200 lines; small enough to read in one sitting. Contains: config loader, paperless client, libretranslate client (with backoff), `chunk_text` generator, Flask routes, worker thread.

- [ ] **Step 1: Create the file**

Path: `roles/composition-paperless-ngx/templates/translator/app.py.j2`

```python
"""Paperless-ngx auto-translation sidecar.

A single-consumer worker pulls document IDs from a Redis queue, fetches
the document content from paperless, applies OCR cleanup, detects the
language via LibreTranslate, translates non-English content in chunks,
and POSTs the translation back to paperless as a Note.

The Flask HTTP surface (/translate, /status, /healthz) is intentionally
small — the queue is the contract, not the API.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import random
import sys
import threading
import time
from typing import Iterator

import redis
import requests
from flask import Flask, jsonify, request

import ocr_cleanup

# ---------------------------------------------------------------------------
# Config (all values come from env; the role renders these via .env file)
# ---------------------------------------------------------------------------
PAPERLESS_URL = os.environ["PAPERLESS_URL"].rstrip("/")
PAPERLESS_API_TOKEN = os.environ["PAPERLESS_API_TOKEN"]
LIBRETRANSLATE_URL = os.environ["LIBRETRANSLATE_URL"].rstrip("/")
LIBRETRANSLATE_API_KEY = os.environ["LIBRETRANSLATE_API_KEY"]
REDIS_URL = os.environ["REDIS_URL"]
TARGET_LANG = os.environ.get("TARGET_LANG", "en")
SKIP_SOURCE_LANGS = {
    s.strip() for s in os.environ.get("SKIP_SOURCE_LANGS", "en").split(",") if s.strip()
}
MIN_CONFIDENCE = float(os.environ.get("MIN_CONFIDENCE", "50"))
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "4000"))
OCR_CLEANUP_ENABLED = os.environ.get("OCR_CLEANUP_ENABLED", "true").lower() == "true"

QUEUE_KEY = "paperless-translate:queue"
COMPLETED_KEY = "paperless-translate:completed"
FAILED_KEY = "paperless-translate:failed"
INFLIGHT_KEY = "paperless-translate:in_flight"
NOTE_PREFIX = "**Auto-translation"
MAX_RETRIES_LT = 5
HTTP_TIMEOUT = 30

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='%(message)s',
)
log = logging.getLogger("translator")


def emit(event: str, **fields):
    record = {"ts": dt.datetime.utcnow().isoformat() + "Z", "event": event, **fields}
    log.info(json.dumps(record))


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------
r = redis.from_url(REDIS_URL, decode_responses=True)


# ---------------------------------------------------------------------------
# Paperless client (inline; small enough)
# ---------------------------------------------------------------------------
def _paperless_headers() -> dict:
    return {
        "Authorization": f"Token {PAPERLESS_API_TOKEN}",
        "Content-Type": "application/json",
    }


def paperless_get_document(doc_id: int) -> dict:
    resp = requests.get(
        f"{PAPERLESS_URL}/api/documents/{doc_id}/",
        headers=_paperless_headers(),
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def paperless_get_notes(doc_id: int) -> list[dict]:
    resp = requests.get(
        f"{PAPERLESS_URL}/api/documents/{doc_id}/notes/",
        headers=_paperless_headers(),
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    body = resp.json()
    return body if isinstance(body, list) else body.get("results", [])


def paperless_add_note(doc_id: int, note: str) -> None:
    resp = requests.post(
        f"{PAPERLESS_URL}/api/documents/{doc_id}/notes/",
        headers=_paperless_headers(),
        json={"note": note},
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()


def already_translated(doc_id: int) -> bool:
    try:
        for n in paperless_get_notes(doc_id):
            note_text = n.get("note") or ""
            if note_text.startswith(NOTE_PREFIX):
                return True
    except requests.RequestException as e:
        emit("paperless.notes.error", doc=doc_id, error=str(e))
    return False


# ---------------------------------------------------------------------------
# LibreTranslate client
# ---------------------------------------------------------------------------
def lt_detect(text: str) -> tuple[str, float]:
    """Return (language, confidence)."""
    sample = text[:2000]
    resp = requests.post(
        f"{LIBRETRANSLATE_URL}/detect",
        json={"q": sample, "api_key": LIBRETRANSLATE_API_KEY},
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    body = resp.json()
    if not body:
        return ("", 0.0)
    top = body[0]
    return (top.get("language", ""), float(top.get("confidence", 0.0)))


def lt_translate_chunk(text: str, source: str) -> str:
    resp = requests.post(
        f"{LIBRETRANSLATE_URL}/translate",
        json={
            "q": text,
            "source": source,
            "target": TARGET_LANG,
            "format": "text",
            "api_key": LIBRETRANSLATE_API_KEY,
        },
        timeout=HTTP_TIMEOUT,
    )
    if resp.status_code == 400:
        # Bad request — likely unsupported language pair. Surface as a typed error.
        raise UnsupportedLanguage(source)
    resp.raise_for_status()
    return resp.json()["translatedText"]


class UnsupportedLanguage(Exception):
    def __init__(self, source: str):
        super().__init__(source)
        self.source = source


# ---------------------------------------------------------------------------
# Chunking — pure function, exercised by unit tests
# ---------------------------------------------------------------------------
def chunk_text(text: str, chunk_size: int) -> Iterator[str]:
    """Yield successive chunks of `text` no longer than `chunk_size`.

    Prefers to split on paragraph boundaries, then sentence boundaries,
    then hard-splits at the size limit.
    """
    if not text:
        return
    if len(text) <= chunk_size:
        yield text
        return

    remaining = text
    while remaining:
        if len(remaining) <= chunk_size:
            yield remaining
            return
        window = remaining[:chunk_size]
        # Prefer paragraph break, then sentence break, then hard cut.
        split_at = window.rfind("\n\n")
        if split_at < chunk_size // 2:
            split_at = window.rfind(". ")
            if split_at > 0:
                split_at += 1  # keep the period with the left chunk
        if split_at < chunk_size // 4:
            split_at = chunk_size
        yield remaining[:split_at]
        remaining = remaining[split_at:].lstrip()


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------
def build_note(translated: str, source: str) -> str:
    ts = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return (
        f"{NOTE_PREFIX} ({source} → {TARGET_LANG}, LibreTranslate)**\n"
        f"_Generated {ts}_\n\n"
        f"{translated}"
    )


def build_skip_note(reason: str) -> str:
    ts = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return f"{NOTE_PREFIX} skipped ({reason})**\n_Checked {ts}_"


def build_failure_note(reason: str) -> str:
    ts = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return f"{NOTE_PREFIX} FAILED**\n_Attempted {ts}_\n\nReason: {reason}"


def process_one(doc_id: int) -> None:
    if already_translated(doc_id):
        emit("skip.already_translated", doc=doc_id)
        r.incr(COMPLETED_KEY)
        return

    try:
        doc = paperless_get_document(doc_id)
    except requests.RequestException as e:
        emit("paperless.get.error", doc=doc_id, error=str(e))
        raise

    content = (doc.get("content") or "").strip()
    if len(content) < 20:
        paperless_add_note(doc_id, build_skip_note("empty content"))
        emit("skip.empty", doc=doc_id)
        r.incr(COMPLETED_KEY)
        return

    if OCR_CLEANUP_ENABLED:
        content = ocr_cleanup.clean(content)

    lang, conf = lt_detect(content)
    emit("detect", doc=doc_id, lang=lang, conf=conf)

    if conf < MIN_CONFIDENCE:
        paperless_add_note(doc_id, build_skip_note("low confidence"))
        r.incr(COMPLETED_KEY)
        return

    if lang in SKIP_SOURCE_LANGS:
        paperless_add_note(doc_id, build_skip_note(f"source: {lang}"))
        r.incr(COMPLETED_KEY)
        return

    try:
        translated_parts = []
        for chunk in chunk_text(content, CHUNK_SIZE):
            translated_parts.append(lt_translate_chunk(chunk, source=lang))
        translated = "\n\n".join(translated_parts)
    except UnsupportedLanguage as e:
        paperless_add_note(doc_id, build_skip_note(f"unsupported source: {e.source}"))
        emit("skip.unsupported", doc=doc_id, lang=e.source)
        r.incr(COMPLETED_KEY)
        return

    paperless_add_note(doc_id, build_note(translated, lang))
    emit("translated", doc=doc_id, lang=lang, chars=len(translated))
    r.incr(COMPLETED_KEY)


def run_worker() -> None:
    """Single-consumer loop. Blocks on BRPOP."""
    emit("worker.start")
    while True:
        try:
            popped = r.brpop(QUEUE_KEY, timeout=0)
        except redis.RedisError as e:
            emit("redis.error", error=str(e))
            time.sleep(5)
            continue

        _, doc_id_raw = popped
        try:
            doc_id = int(doc_id_raw)
        except ValueError:
            emit("worker.bad_payload", payload=doc_id_raw)
            continue

        r.set(INFLIGHT_KEY, doc_id)
        attempt = 0
        while True:
            try:
                process_one(doc_id)
                break
            except requests.RequestException as e:
                attempt += 1
                if attempt > MAX_RETRIES_LT:
                    try:
                        paperless_add_note(doc_id, build_failure_note(str(e)))
                    except requests.RequestException:
                        pass
                    r.incr(FAILED_KEY)
                    emit("worker.fail", doc=doc_id, error=str(e))
                    break
                delay = min(16, 2 ** (attempt - 1)) + random.uniform(0, 0.5)
                emit("worker.retry", doc=doc_id, attempt=attempt, sleep=round(delay, 2), error=str(e))
                time.sleep(delay)
        r.delete(INFLIGHT_KEY)


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------
app = Flask(__name__)


@app.post("/translate")
def http_translate():
    data = request.get_json(silent=True) or {}
    doc_id = data.get("document_id")
    if not isinstance(doc_id, int):
        return jsonify({"error": "document_id (int) required"}), 400
    if already_translated(doc_id):
        return jsonify({"already_processed": True, "document_id": doc_id}), 200
    r.lpush(QUEUE_KEY, doc_id)
    return jsonify({"queued": True, "document_id": doc_id}), 202


@app.get("/status")
def http_status():
    return jsonify({
        "queued": r.llen(QUEUE_KEY),
        "in_flight": 1 if r.exists(INFLIGHT_KEY) else 0,
        "completed_total": int(r.get(COMPLETED_KEY) or 0),
        "failed_total": int(r.get(FAILED_KEY) or 0),
    }), 200


@app.get("/healthz")
def http_healthz():
    checks = {"redis": False, "libretranslate": False, "paperless": False}
    try:
        checks["redis"] = bool(r.ping())
    except redis.RedisError:
        pass
    try:
        checks["libretranslate"] = requests.get(
            f"{LIBRETRANSLATE_URL}/languages", timeout=5
        ).ok
    except requests.RequestException:
        pass
    try:
        checks["paperless"] = requests.get(
            f"{PAPERLESS_URL}/api/", headers=_paperless_headers(), timeout=5
        ).status_code < 500
    except requests.RequestException:
        pass
    ok = all(checks.values())
    return jsonify(checks), (200 if ok else 503)


def _start_worker_once():
    t = threading.Thread(target=run_worker, name="translator-worker", daemon=True)
    t.start()


_start_worker_once()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

- [ ] **Step 2: Commit**

```bash
git add roles/composition-paperless-ngx/templates/translator/app.py.j2
git commit -m "feat(composition-paperless-ngx): add translator service code"
```

---

## Task 7: Write the Dockerfile

**Files:**
- Create: `roles/composition-paperless-ngx/templates/translator/Dockerfile.j2`

**Why:** Custom image so deps are pinned and tests run at build time (deploy fails fast on regression).

- [ ] **Step 1: Create the Dockerfile**

Path: `roles/composition-paperless-ngx/templates/translator/Dockerfile.j2`

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ocr_cleanup.py /app/ocr_cleanup.py
COPY app.py /app/app.py
COPY test_translator.py /app/test_translator.py

# Provide harmless defaults so pytest can import app.py without env errors.
ENV PAPERLESS_URL=http://placeholder \
    PAPERLESS_API_TOKEN=placeholder \
    LIBRETRANSLATE_URL=http://placeholder \
    LIBRETRANSLATE_API_KEY=placeholder \
    REDIS_URL=redis://placeholder:6379/1
RUN pytest -q test_translator.py

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fs http://localhost:5000/healthz || exit 1

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--access-logfile", "-", "app:app"]
```

Note: tests run during `docker build`, so a regression in pure functions fails the deploy instead of the runtime.

- [ ] **Step 2: Commit**

```bash
git add roles/composition-paperless-ngx/templates/translator/Dockerfile.j2
git commit -m "feat(composition-paperless-ngx): add translator Dockerfile"
```

---

## Task 8: Write the post-consume script

**Files:**
- Create: `roles/composition-paperless-ngx/templates/scripts/post_consume.sh.j2`

**Why:** Paperless invokes this with `DOCUMENT_ID` (and other) env vars set. Fire-and-forget; never blocks paperless's consumer worker.

- [ ] **Step 1: Create the script**

Path: `roles/composition-paperless-ngx/templates/scripts/post_consume.sh.j2`

```bash
#!/bin/sh
# Fire-and-forget hook called by paperless-ngx after a document is consumed.
# Paperless sets DOCUMENT_ID in the environment. We never block on the response.

set -u

if [ -z "${DOCUMENT_ID:-}" ]; then
    echo "post_consume: DOCUMENT_ID not set; nothing to do"
    exit 0
fi

curl --max-time 5 -fsS \
    -X POST \
    -H "Content-Type: application/json" \
    -d "{\"document_id\": ${DOCUMENT_ID}}" \
    http://translator:5000/translate \
    >/dev/null 2>&1 \
    || echo "post_consume: translator unreachable for doc ${DOCUMENT_ID} (queued? no)"

exit 0
```

- [ ] **Step 2: Commit**

```bash
git add roles/composition-paperless-ngx/templates/scripts/post_consume.sh.j2
git commit -m "feat(composition-paperless-ngx): add post-consume hook"
```

---

## Task 9: Modify the compose template

**Files:**
- Modify: `roles/composition-paperless-ngx/templates/docker-compose.yaml.j2`

**Why:** Wire the translator service into compose, mount the post-consume script into the webserver, set the env var, declare ordering.

- [ ] **Step 1: Replace the webserver block to add the post-consume env, volume, and dependency**

Find:

```yaml
  webserver:
    container_name: paperless_webserver
    image: ghcr.io/paperless-ngx/paperless-ngx:latest
    restart: unless-stopped
    env_file: .environment_vars
    depends_on:
      db:
        condition: service_healthy
      broker:
        condition: service_healthy
      gotenberg:
        condition: service_started
      tika:
        condition: service_started
    volumes:
      - "{{ composition_config }}/data:/usr/src/paperless/data"
      - "{{ composition_config }}/media:/usr/src/paperless/media"
      - "{{ composition_config }}/export:/usr/src/paperless/export"
      - "{{ composition_config }}/consume:/usr/src/paperless/consume"
      - /etc/localtime:/etc/localtime:ro
```

Replace with:

```yaml
  webserver:
    container_name: paperless_webserver
    image: ghcr.io/paperless-ngx/paperless-ngx:latest
    restart: unless-stopped
    env_file: .environment_vars
{% if paperless_ngx_translate_enabled %}
    environment:
      PAPERLESS_POST_CONSUME_SCRIPT: "/usr/src/paperless/scripts/post_consume.sh"
{% endif %}
    depends_on:
      db:
        condition: service_healthy
      broker:
        condition: service_healthy
      gotenberg:
        condition: service_started
      tika:
        condition: service_started
{% if paperless_ngx_translate_enabled %}
      translator:
        condition: service_started
{% endif %}
    volumes:
      - "{{ composition_config }}/data:/usr/src/paperless/data"
      - "{{ composition_config }}/media:/usr/src/paperless/media"
      - "{{ composition_config }}/export:/usr/src/paperless/export"
      - "{{ composition_config }}/consume:/usr/src/paperless/consume"
{% if paperless_ngx_translate_enabled %}
      - "{{ composition_config }}/scripts:/usr/src/paperless/scripts:ro"
{% endif %}
      - /etc/localtime:/etc/localtime:ro
```

- [ ] **Step 2: Add the translator service block above the `networks:` section**

Insert this block immediately before the existing `networks:` line at the bottom of the file:

```yaml
{% if paperless_ngx_translate_enabled %}
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
{% endif %}

```

- [ ] **Step 3: Verify the template is still valid YAML when rendered with the default**

Run from the repo root:

```bash
python3 -c "
import jinja2, yaml
src = open('roles/composition-paperless-ngx/templates/docker-compose.yaml.j2').read()
rendered = jinja2.Environment(undefined=jinja2.DebugUndefined).from_string(src).render(
    composition_name='paperless-ngx',
    composition_config='/data/paperless-ngx/config',
    default_docker_network='infra',
    domainname_infra='example.com',
    paperless_ngx_translate_enabled=True,
)
yaml.safe_load(rendered)
print('OK')
"
```

Expected: `OK`. (Re-run with `paperless_ngx_translate_enabled=False` and confirm the translator block is absent.)

- [ ] **Step 4: Commit**

```bash
git add roles/composition-paperless-ngx/templates/docker-compose.yaml.j2
git commit -m "feat(composition-paperless-ngx): wire translator into compose"
```

---

## Task 10: Modify tasks/main.yaml

**Files:**
- Modify: `roles/composition-paperless-ngx/tasks/main.yaml`

**Why:** Create the new dirs, render the new templates, render a new env-file specifically for the translator. All new tasks are gated on `paperless_ngx_translate_enabled`.

- [ ] **Step 1: Extend the existing `Create directories` loop**

Find:

```yaml
- name: Create directories
  ansible.builtin.file:
    path: "{{ composition_config }}/{{ dir_item }}"
    state: directory
  loop_control:
    loop_var: dir_item
  loop:
    - postgres
    - data
    - media
    - export
    - consume
```

Replace with:

```yaml
- name: Create directories
  ansible.builtin.file:
    path: "{{ composition_config }}/{{ dir_item }}"
    state: directory
  loop_control:
    loop_var: dir_item
  loop:
    - postgres
    - data
    - media
    - export
    - consume

- name: Create translation directories
  ansible.builtin.file:
    path: "{{ composition_config }}/{{ dir_item }}"
    state: directory
  loop_control:
    loop_var: dir_item
  loop:
    - scripts
    - translator
  when: paperless_ngx_translate_enabled
```

- [ ] **Step 2: Add tasks to render the new files**

Immediately before the `- name: Run Configure DNS role` task, insert:

```yaml
- name: Render translator build context
  ansible.builtin.template:
    src: "translator/{{ tpl_item }}.j2"
    dest: "{{ composition_config }}/translator/{{ tpl_item }}"
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0644"
  loop_control:
    loop_var: tpl_item
  loop:
    - Dockerfile
    - requirements.txt
    - app.py
    - ocr_cleanup.py
    - test_translator.py
  when: paperless_ngx_translate_enabled
  notify: Rebuild translator

- name: Render post-consume script
  ansible.builtin.template:
    src: scripts/post_consume.sh.j2
    dest: "{{ composition_config }}/scripts/post_consume.sh"
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0755"
  when: paperless_ngx_translate_enabled

- name: Render translator env file
  ansible.builtin.template:
    src: environment_vars_translator.j2
    dest: "{{ composition_root }}/.environment_vars_translator"
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0660"
  when: paperless_ngx_translate_enabled
```

- [ ] **Step 3: Commit**

```bash
git add roles/composition-paperless-ngx/tasks/main.yaml
git commit -m "feat(composition-paperless-ngx): render translator templates"
```

---

## Task 11: Add the translator env-file template

**Files:**
- Create: `roles/composition-paperless-ngx/templates/environment_vars_translator.j2`

**Why:** Keeps the translator's secrets compartmentalised — the webserver container never sees the LibreTranslate API key, and vice versa. Compose's `env_file` is per-service so this just works.

- [ ] **Step 1: Create the file**

Path: `roles/composition-paperless-ngx/templates/environment_vars_translator.j2`

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

- [ ] **Step 2: Commit**

```bash
git add roles/composition-paperless-ngx/templates/environment_vars_translator.j2
git commit -m "feat(composition-paperless-ngx): add translator env file template"
```

---

## Task 12: Add a `Rebuild translator` handler

**Files:**
- Create: `roles/composition-paperless-ngx/handlers/main.yaml`

**Why:** When any template under `translator/` changes, the image needs rebuilding before compose-up. A handler keeps that out of the main task path while still triggering on changes.

- [ ] **Step 1: Create the handlers directory and file**

Path: `roles/composition-paperless-ngx/handlers/main.yaml`

```yaml
# code: language=ansible

- name: Rebuild translator
  community.docker.docker_compose_v2_build:
    project_src: "{{ composition_root }}"
    services:
      - translator
```

- [ ] **Step 2: Commit**

```bash
git add roles/composition-paperless-ngx/handlers/main.yaml
git commit -m "feat(composition-paperless-ngx): add translator rebuild handler"
```

---

## Task 13: Add a README for the role

**Files:**
- Create: `roles/composition-paperless-ngx/README.md`

**Why:** Other compositions in this repo have READMEs (`composition-libretranslate/README.md`, `composition-grafana/README.md`, etc.). Following the convention.

- [ ] **Step 1: Create the README**

Path: `roles/composition-paperless-ngx/README.md`

```markdown
# Paperless-ngx

Document management with full-text search, OCR, and (optionally) automatic
translation of non-English documents into English on ingest.

## Services

| Service | Purpose |
|---------|---------|
| `webserver` | Paperless-ngx (UI + consumer worker) |
| `db` | Postgres 16 |
| `broker` | Redis 8 (paperless celery + translator queue, separate DB indices) |
| `gotenberg` | Office/PDF conversion |
| `tika` | Text extraction |
| `translator` | Auto-translation sidecar (optional, see below) |

## Auto-translation

When `paperless_ngx_translate_enabled` is `true` (default), a custom `translator`
service is built and run. It reuses the existing
[`composition-libretranslate`](../composition-libretranslate/README.md) instance
on the same host via the shared `default_docker_network`.

On each consumed document, paperless invokes the post-consume hook (a small
shell script mounted into the webserver) which fires a fire-and-forget POST to
the translator. The translator enqueues the job onto Redis DB index 1, a single
worker thread picks it up, detects the language via LibreTranslate, applies OCR
cleanup, translates non-English content in chunks, and POSTs the result back to
paperless as a Note prefixed `**Auto-translation`.

The original OCR `content` field is never modified.

### Manual triggers

The translator exposes the following internal HTTP endpoints (not Traefik-fronted):

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/translate` | Body `{"document_id": N}` — enqueue a translation |
| `GET`  | `/status`    | Queue + counter snapshot |
| `GET`  | `/healthz`   | Redis + LibreTranslate + paperless reachability |

From the host:

```bash
docker exec paperless_webserver curl -fsS http://translator:5000/status
```

### Kill switch

`paperless_ngx_translate_enabled: false` removes the translator service from
compose, drops the post-consume env var, and skips rendering the translator
build context. Paperless continues to operate normally.

## DNS

Registers subdomain: `paperless`.

## Vault entries (per host)

| Variable | Purpose |
|---|---|
| `vault_paperless_ngx_db_password` | Postgres password |
| `vault_paperless_ngx_secret_key` | Django secret key |
| `vault_paperless_ngx_admin_password` | Initial admin password |
| `vault_paperless_ngx_admin_mail` | Initial admin email |
| `vault_paperless_ngx_libretranslate_api_key` | LibreTranslate API key (required when translation enabled) |
| `vault_paperless_ngx_api_token` | Paperless REST API token (required when translation enabled) |
```

- [ ] **Step 2: Commit**

```bash
git add roles/composition-paperless-ngx/README.md
git commit -m "docs(composition-paperless-ngx): add role README"
```

---

## Task 14: Local linting

**Files:**
- All changed files

**Why:** Catch trailing whitespace, YAML errors, and ansible-lint warnings before hitting the server.

- [ ] **Step 1: Run pre-commit on all changed files**

```bash
pre-commit run --files \
    inventory/host_vars/server-64gb-storage/vault_paperless_ngx.yaml \
    roles/composition-paperless-ngx/defaults/main.yaml \
    roles/composition-paperless-ngx/tasks/main.yaml \
    roles/composition-paperless-ngx/handlers/main.yaml \
    roles/composition-paperless-ngx/README.md \
    roles/composition-paperless-ngx/templates/docker-compose.yaml.j2 \
    roles/composition-paperless-ngx/templates/environment_vars_translator.j2 \
    roles/composition-paperless-ngx/templates/scripts/post_consume.sh.j2 \
    roles/composition-paperless-ngx/templates/translator/Dockerfile.j2 \
    roles/composition-paperless-ngx/templates/translator/requirements.txt.j2 \
    roles/composition-paperless-ngx/templates/translator/app.py.j2 \
    roles/composition-paperless-ngx/templates/translator/ocr_cleanup.py.j2 \
    roles/composition-paperless-ngx/templates/translator/test_translator.py.j2
```

Expected: all hooks pass. If `end-of-file-fixer` or `trailing-whitespace` rewrites a file, stage the change and commit with `chore: pre-commit cleanup`.

- [ ] **Step 2: Ansible syntax check**

```bash
ansible-playbook --syntax-check playbooks/hosts/server-64gb-storage/core.yaml
```

Expected: prints the playbook path with no errors.

- [ ] **Step 3 (optional but recommended): ansible-lint the role**

```bash
ansible-lint roles/composition-paperless-ngx/
```

Triage any warnings. Yamllint warnings inside `templates/*.j2` are expected (Jinja syntax confuses YAML linters) and are excluded by the pre-commit config.

---

## Task 15: Deploy to `server-64gb-storage`

**Files:**
- None modified; deployment only

- [ ] **Step 1: Confirm libretranslate is healthy**

```bash
ssh server-storage 'docker ps --filter name=libretranslate --format "{{ "{{.Status}}" }}"'
```

Expected: `Up <duration> (healthy)`.

- [ ] **Step 2: Run the host playbook with the composition tag**

```bash
ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml \
    --tags compositions \
    --start-at-task "composition-paperless-ngx"
```

If `--start-at-task` is not honoured by your collection version, simply run with `--tags compositions` and let the run reach paperless naturally.

Expected: `composition-paperless-ngx : Start Docker Compose project` reports `changed=1`. The handler `Rebuild translator` should fire (look for it in the play recap).

- [ ] **Step 3: Confirm both new container artefacts exist on the host**

```bash
ssh server-storage 'docker ps --format "table {{ "{{.Names}}" }}\t{{ "{{.Status}}" }}" | grep paperless'
```

Expected: at minimum `paperless_webserver` and `paperless_translator` both `Up … (healthy)` or `(starting)`.

---

## Task 16: Post-deploy verification

**Files:**
- None modified; verification only

- [ ] **Step 1: Translator healthz**

```bash
ssh server-storage 'docker exec paperless_translator curl -fsS http://localhost:5000/healthz'
```

Expected JSON: `{"libretranslate": true, "paperless": true, "redis": true}`.

- [ ] **Step 2: Confirm the post-consume script is in place inside the webserver**

```bash
ssh server-storage 'docker exec paperless_webserver cat /usr/src/paperless/scripts/post_consume.sh | head -5'
```

Expected: the first lines of the shell script.

- [ ] **Step 3: Confirm paperless picked up the env var**

```bash
ssh server-storage 'docker exec paperless_webserver printenv PAPERLESS_POST_CONSUME_SCRIPT'
```

Expected: `/usr/src/paperless/scripts/post_consume.sh`.

- [ ] **Step 4: End-to-end smoke — upload one foreign-language doc**

Via the paperless UI on `https://paperless.{{ domainname_infra }}`, upload a known German PDF (or any non-English doc). Within ~30 seconds, open the document; a Note starting with `**Auto-translation (de → en, LibreTranslate)**` should be present.

- [ ] **Step 5: Idempotency check**

From your workstation:

```bash
DOC_ID=<the id you just uploaded>
ssh server-storage \
    "docker exec paperless_translator curl -fsS -X POST -H 'Content-Type: application/json' \
        -d '{\"document_id\": ${DOC_ID}}' http://localhost:5000/translate"
```

Expected JSON: `{"already_processed": true, "document_id": <id>}`. No second note appears in the UI.

- [ ] **Step 6: Counter check**

```bash
ssh server-storage 'docker exec paperless_translator curl -fsS http://localhost:5000/status'
```

Expected: `completed_total` ≥ 1, `failed_total` = 0, `queued` = 0, `in_flight` = 0.

- [ ] **Step 7: Skim translator logs for noise**

```bash
ssh server-storage 'docker logs paperless_translator --tail 100'
```

Expected: structured JSON lines, no Python tracebacks, no LibreTranslate auth failures.

---

## Self-Review

**1. Spec coverage**

| Spec section | Implemented in |
|---|---|
| Architecture: new translator service | Task 6 (`app.py.j2`), Task 7 (Dockerfile), Task 9 (compose) |
| Reuse `composition-libretranslate` | Task 1 (vault key from LT), Task 11 (env points at `libretranslate:5000`) |
| Reuse redis broker on DB index 1 | Task 11 (env: `REDIS_URL=redis://broker:6379/1`) |
| Post-consume hook | Task 8, Task 9 (env + mount), Task 10 (script render) |
| Notes-based output, not Content modification | Task 6 (`paperless_add_note`) |
| Idempotency via `**Auto-translation` prefix | Task 6 (`already_translated`, pre-enqueue and pre-write) |
| Skip conditions (English, low confidence, empty, unsupported) | Task 6 (`process_one`) |
| OCR cleanup ported from reference repo | Task 4 |
| Chunking | Task 6 (`chunk_text`), Task 5 (tests) |
| Vault: LT API key + paperless token | Task 1 |
| Kill switch (`paperless_ngx_translate_enabled`) | Task 2, Task 9, Task 10 |
| `/translate`, `/status`, `/healthz` endpoints | Task 6 |
| Compose healthcheck | Task 7 (Dockerfile `HEALTHCHECK`), Task 9 (compose `healthcheck`) |
| Structured JSON logs (Loki-friendly) | Task 6 (`emit`) |
| Pre-commit / linting | Task 14 |
| Verification checklist | Task 15, Task 16 |

No gaps identified.

**2. Placeholder scan** — none. Every code block is concrete.

**3. Type consistency**

- `chunk_text(text, chunk_size)` — same signature in `app.py.j2` (Task 6) and in tests (Task 5).
- `ocr_cleanup.clean(text)` — defined in Task 4, called from `process_one` in Task 6.
- Vault names: `vault_paperless_ngx_libretranslate_api_key`, `vault_paperless_ngx_api_token` — consistent across Task 1, Task 2, Task 11, and the README in Task 13.
- Note prefix `**Auto-translation` — used in `NOTE_PREFIX` (Task 6) and the README (Task 13). Consistent.
- Redis keys (`paperless-translate:queue`, `:completed`, `:failed`, `:in_flight`) — defined and used in the same file (Task 6).

Plan is internally consistent.

---

## Execution

Plan complete and saved to `docs/superpowers/plans/2026-05-30-paperless-ngx-auto-translation.md`. Two execution options:

1. **Subagent-Driven (recommended)** — A fresh subagent runs each task; the main session reviews between tasks. Faster end-to-end and keeps any single agent's context narrow.
2. **Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, with checkpoints for review.

Which approach?
