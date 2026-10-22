"""Paperless-ngx 3.x compatibility shim for pdf-translate-webhook 0.2.1.

Upstream poll_task() expects the Paperless 2.x tasks API (status "SUCCESS",
"related_document"). Paperless 3.x returns status "success" and the new
document in "result_data.document_id" / "related_document_ids", so every
companion upload ends as "uploaded_unlinked".

Python imports this module at start-up (PYTHONPATH), for both the uvicorn
server and `python backfill.py`. Remove it once upstream handles 3.x.
"""

import sys
import time

sys.path.insert(0, "/app")

try:
    import webhook
except Exception:  # not running in the webhook image
    webhook = None


def _poll_task(client, task_uuid, max_wait=120):
    deadline = time.time() + max_wait
    while time.time() < deadline:
        time.sleep(3)
        try:
            data = webhook._pl_get(client, f"/api/tasks/?task_id={task_uuid}")
            tasks = data if isinstance(data, list) else data.get("results", [])
            if not tasks:
                continue
            task = tasks[0]
            status = str(task.get("status", "")).upper()
            if status == "SUCCESS":
                doc_id = (
                    (task.get("result_data") or {}).get("document_id")
                    or next(iter(task.get("related_document_ids") or []), None)
                    or task.get("related_document")
                )
                return int(doc_id) if doc_id else None
            if status in ("FAILURE", "REVOKED"):
                return None
        except Exception:
            pass
    return None


if webhook is not None:
    webhook.poll_task = _poll_task
