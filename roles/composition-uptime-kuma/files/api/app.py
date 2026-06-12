"""REST API sidecar for Uptime Kuma.

Bridges Ansible (and any HTTP caller) to Uptime Kuma's internal Socket.IO
API via the uptime-kuma-api Python package. Exposes a small set of endpoints
protected by an X-API-Key header.

Designed to run as a long-lived process inside the same Docker Compose
stack as uptime-kuma. Connects lazily on first request and reconnects if
the underlying Socket.IO session goes stale.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Callable, Optional

from flask import Flask, jsonify, request
from uptime_kuma_api import MonitorType, UptimeKumaApi

log = logging.getLogger("uptime-kuma-api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


_MONITOR_TYPES = {
    "ping": MonitorType.PING,
    "http": MonitorType.HTTP,
}


def _default_uptime_api_factory() -> UptimeKumaApi:
    """Build and log in to a real UptimeKumaApi instance."""
    url = os.environ["UPTIME_KUMA_URL"]
    username = os.environ["UPTIME_KUMA_USERNAME"]
    password = os.environ["UPTIME_KUMA_PASSWORD"]
    log.info("connecting to uptime-kuma at %s", url)
    api = UptimeKumaApi(url, timeout=30)
    api.login(username, password)
    return api


def create_app(
    uptime_api_factory: Optional[Callable[[], UptimeKumaApi]] = None,
) -> Flask:
    """Application factory. Pass uptime_api_factory for tests to inject a mock."""
    app = Flask(__name__)
    api_key = os.environ["API_KEY"]
    monitor_tag = os.environ.get("MONITOR_TAG", "ansible-managed")
    factory = uptime_api_factory or _default_uptime_api_factory

    session_lock = threading.Lock()
    session: dict = {"api": None}

    def get_api() -> UptimeKumaApi:
        with session_lock:
            if session["api"] is None:
                session["api"] = factory()
            return session["api"]

    def invalidate_session() -> None:
        """Clear the cached session so the next get_api() call reconnects."""
        with session_lock:
            session["api"] = None

    def require_api_key() -> Optional[tuple]:
        if request.headers.get("X-API-Key") != api_key:
            return jsonify({"error": "unauthorized"}), 401
        return None

    def ensure_tag_id(api: UptimeKumaApi) -> int:
        """Return id of the ansible-managed tag, creating it if missing."""
        for tag in api.get_tags():
            if tag["name"] == monitor_tag:
                return tag["id"]
        created = api.add_tag(name=monitor_tag, color="#7c8eef")
        return created["id"]

    def tag_names(monitor: dict) -> list:
        return [t.get("name") for t in monitor.get("tags") or []]

    def build_add_monitor_kwargs(spec: dict) -> dict:
        mtype = spec.get("type")
        if mtype not in _MONITOR_TYPES:
            raise ValueError(f"unknown monitor type: {mtype!r}")
        name = spec.get("name")
        if not name:
            raise ValueError("monitor 'name' is required")
        kwargs = {"type": _MONITOR_TYPES[mtype], "name": name}
        if mtype == "http":
            url = spec.get("url")
            if not url:
                raise ValueError("http monitor requires 'url'")
            kwargs["url"] = url
        elif mtype == "ping":
            hostname = spec.get("hostname")
            if not hostname:
                raise ValueError("ping monitor requires 'hostname'")
            kwargs["hostname"] = hostname
        return kwargs

    def create_and_tag(api: UptimeKumaApi, spec: dict) -> int:
        kwargs = build_add_monitor_kwargs(spec)
        result = api.add_monitor(**kwargs)
        monitor_id = result.get("monitorID") or result.get("monitorId")
        tag_id = ensure_tag_id(api)
        api.add_monitor_tag(tag_id=tag_id, monitor_id=monitor_id, value="")
        return monitor_id

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/monitors", methods=["GET"])
    def list_monitors():
        unauth = require_api_key()
        if unauth:
            return unauth
        try:
            api = get_api()
            return jsonify(api.get_monitors()), 200
        except Exception as exc:
            invalidate_session()
            log.warning("list_monitors failed, session invalidated: %s", exc)
            return jsonify({"error": "upstream error"}), 502

    @app.route("/monitors", methods=["POST"])
    def create_monitor():
        unauth = require_api_key()
        if unauth:
            return unauth
        spec = request.get_json(silent=True) or {}
        try:
            api = get_api()
            monitor_id = create_and_tag(api, spec)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            invalidate_session()
            log.warning("create_monitor failed, session invalidated: %s", exc)
            return jsonify({"error": "upstream error"}), 502
        return jsonify({"monitorID": monitor_id, "msg": "Added Successfully."}), 201

    @app.route("/monitors/<int:monitor_id>", methods=["DELETE"])
    def delete_monitor(monitor_id: int):
        unauth = require_api_key()
        if unauth:
            return unauth
        try:
            api = get_api()
            api.delete_monitor(monitor_id)
        except Exception as exc:
            invalidate_session()
            log.warning("delete_monitor failed, session invalidated: %s", exc)
            return jsonify({"error": "upstream error"}), 502
        return jsonify({"msg": "Deleted Successfully."}), 200

    @app.route("/monitors/sync", methods=["POST"])
    def sync_monitors():
        unauth = require_api_key()
        if unauth:
            return unauth
        payload = request.get_json(silent=True) or {}
        if "monitors" not in payload:
            return jsonify({"error": "body must contain 'monitors' key"}), 400
        desired = payload["monitors"]
        desired_names = {m["name"] for m in desired if m.get("name")}

        try:
            api = get_api()
            existing = api.get_monitors()
        except Exception as exc:
            invalidate_session()
            log.warning("sync_monitors failed to fetch monitors, session invalidated: %s", exc)
            return jsonify({"error": "upstream error"}), 502
        managed = [m for m in existing if monitor_tag in tag_names(m)]
        managed_by_name = {m["name"]: m for m in managed}

        created = 0
        skipped = 0
        deleted = 0
        errors = []

        for spec in desired:
            name = spec.get("name")
            if not name:
                errors.append({"spec": spec, "error": "missing name"})
                continue
            if name in managed_by_name:
                skipped += 1
                continue
            try:
                create_and_tag(api, spec)
                created += 1
            except ValueError as exc:
                errors.append({"spec": spec, "error": str(exc)})
            except Exception as exc:
                invalidate_session()
                log.warning("create_and_tag failed, session invalidated: %s", exc)
                errors.append({"spec": spec, "error": str(exc)})

        for name, monitor in managed_by_name.items():
            if name not in desired_names:
                try:
                    api.delete_monitor(monitor["id"])
                    deleted += 1
                except Exception as exc:
                    errors.append({"name": name, "error": str(exc)})

        return jsonify({
            "created": created,
            "deleted": deleted,
            "skipped": skipped,
            "errors": errors,
        }), 200

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5001)
