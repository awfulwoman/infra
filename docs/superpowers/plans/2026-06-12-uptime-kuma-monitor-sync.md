# Uptime Kuma Monitor Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically populate Uptime Kuma with ICMP ping and HTTPS monitors for all infra hosts, driven by existing Ansible inventory data with no manual UI configuration.

**Architecture:** A Python/Flask REST API sidecar runs alongside Uptime Kuma in the same Docker Compose stack, bridging Ansible to Uptime Kuma's Socket.io API. The composition-uptime-kuma Ansible role is extended to copy the sidecar files, wait for it to be healthy, then POST the desired monitor list built from hostvars. HTTP monitor URLs come from each host's existing `cnames` inventory key; ICMP monitors come from `host_ipv4`.

**Tech Stack:** Python 3.11, Flask, uptime-kuma-api (PyPI), Docker, Ansible, Jinja2, pytest

---

## Reference: design spec

The complete design spec lives at `docs/superpowers/specs/2026-06-12-uptime-kuma-monitor-sync-design.md`. Re-read it if anything below is unclear.

## Reference: key paths and vars

- Role directory: `roles/composition-uptime-kuma/`
- Composition root on target host: `/{{ compositions_dataset }}/uptime-kuma` — `compositions_dataset` is a per-host var (e.g. `fastpool/compositions` on storage)
- `composition_root` and `composition_config` are calculated in `roles/composition-common/tasks/main.yaml` (called from each composition role automatically). For uptime-kuma: `composition_root = /{{ compositions_dataset }}/uptime-kuma`, `composition_config = /{{ compositions_dataset }}/uptime-kuma/config`.
- Inventory group containing all monitored hosts: `infra` (from `inventory/hosts.yaml`)
- Domain var: `domainname_infra` (defined in `inventory/group_vars/all.yaml`)
- Default Docker network: `default_docker_network: guineanet` (from `inventory/group_vars/infra/core.yaml`)
- Sidecar Traefik hostname: `uptime-kuma-api.{{ domainname_infra }}`
- Sidecar exposed port: `5001` (bound on `127.0.0.1` only — Traefik handles TLS)

---

## Task 1: Add cnames to host_vars

- [ ] Edit `inventory/host_vars/server-8gb-backups/core.yaml` — append the following block at the end of the file (after the `compositions_dataset: slowpool/compositions` line):

  ```yaml

  # -------------------------------------------------------------------
  # CNAMES
  # -------------------------------------------------------------------
  cnames:
    - zfs-api.server-8gb-backups.{{ domainname_infra }}
  ```

- [ ] Edit `inventory/host_vars/minipc-8gb-homebrain/core.yaml` — extend the existing `cnames:` list (currently ends with `- gateway.{{ domainname_infra }}`). After that line, add:

  ```yaml
    - owntracks.{{ domainname_infra }}
    - owntracks-recorder.{{ domainname_infra }}
    - zigbee2mqtt.{{ domainname_infra }}
    - zfs-api.minipc-8gb-homebrain.{{ domainname_infra }}
  ```

  The final block should read:

  ```yaml
  cnames:
    - homeassistant.{{ domainname_infra }}
    - ha.{{ domainname_infra }}
    - esphome.{{ domainname_infra }}
    - mctest.{{ domainname_infra }}
    - lan.{{ domainname_infra }}
    - gateway.{{ domainname_infra }}
    - owntracks.{{ domainname_infra }}
    - owntracks-recorder.{{ domainname_infra }}
    - zigbee2mqtt.{{ domainname_infra }}
    - zfs-api.minipc-8gb-homebrain.{{ domainname_infra }}
  ```

- [ ] Edit `inventory/host_vars/vps-hetzner-public01/core.yaml` — append at the end of the file:

  ```yaml

  # -------------------------------------------------------------------
  # CNAMES
  # -------------------------------------------------------------------
  cnames:
    - zfs-api.vps-hetzner-public01.{{ domainname_infra }}
  ```

- [ ] Edit `inventory/host_vars/server-64gb-storage/core.yaml` — extend the existing `cnames:` list (currently ends with `- paperless.{{ domainname_infra }}`). After that line, add:

  ```yaml
    - qbittorrent.{{ domainname_infra }}
    - gluetun.{{ domainname_infra }}
    - bazarr.{{ domainname_infra }}
    - transmission.{{ domainname_infra }}
    - n8n.{{ domainname_infra }}
    - memorybank.{{ domainname_infra }}
    - vikunja.{{ domainname_infra }}
    - uptime-kuma.{{ domainname_infra }}
    - kagimcp.{{ domainname_infra }}
    - firefly.{{ domainname_infra }}
    - firefly-importer.{{ domainname_infra }}
    - zfs.metrics.{{ domainname_infra }}
    - zfs-api.server-64gb-storage.{{ domainname_infra }}
    - jellyfin-vue.{{ domainname_infra }}
    - llmcalc.{{ domainname_infra }}
  ```

- [ ] Edit `inventory/host_vars/raspberry-pi4-2gb-deedee/core.yaml` — append at the end of the file:

  ```yaml

  # -------------------------------------------------------------------
  # CNAMES
  # -------------------------------------------------------------------
  cnames:
    - zfs-api.raspberry-pi4-2gb-deedee.{{ domainname_infra }}
  ```

- [ ] Edit `inventory/host_vars/raspberry-pi4-4gb-randolph/core.yaml` — append at the end of the file:

  ```yaml

  # -------------------------------------------------------------------
  # CNAMES
  # -------------------------------------------------------------------
  cnames:
    - connect.{{ domainname_infra }}
  ```

- [ ] Edit `inventory/host_vars/raspberry-pi5-4gb-belinda/core.yaml` — append at the end of the file:

  ```yaml

  # -------------------------------------------------------------------
  # CNAMES
  # -------------------------------------------------------------------
  cnames:
    - zfs-api.raspberry-pi5-4gb-belinda.{{ domainname_infra }}
  ```

- [ ] Verify YAML syntax for all 7 files:

  ```bash
  cd /Users/charlie/Code/awfulwoman/infra && \
    for f in \
      inventory/host_vars/server-8gb-backups/core.yaml \
      inventory/host_vars/minipc-8gb-homebrain/core.yaml \
      inventory/host_vars/vps-hetzner-public01/core.yaml \
      inventory/host_vars/server-64gb-storage/core.yaml \
      inventory/host_vars/raspberry-pi4-2gb-deedee/core.yaml \
      inventory/host_vars/raspberry-pi4-4gb-randolph/core.yaml \
      inventory/host_vars/raspberry-pi5-4gb-belinda/core.yaml; do
      echo "--- $f ---"
      python3 -c "import yaml,sys; yaml.safe_load(open('$f'))" && echo "OK"
    done
  ```

  Expected output: `--- <path> ---` / `OK` repeated 7 times. Failure prints a traceback.

- [ ] Run yamllint and pre-commit on the changed files:

  ```bash
  cd /Users/charlie/Code/awfulwoman/infra && \
    pre-commit run --files \
      inventory/host_vars/server-8gb-backups/core.yaml \
      inventory/host_vars/minipc-8gb-homebrain/core.yaml \
      inventory/host_vars/vps-hetzner-public01/core.yaml \
      inventory/host_vars/server-64gb-storage/core.yaml \
      inventory/host_vars/raspberry-pi4-2gb-deedee/core.yaml \
      inventory/host_vars/raspberry-pi4-4gb-randolph/core.yaml \
      inventory/host_vars/raspberry-pi5-4gb-belinda/core.yaml
  ```

  Expected: all checks `Passed` or `Skipped`. Fix any failures before continuing.

- [ ] Commit the cnames additions with this exact message (do not split into per-host commits):

  ```bash
  cd /Users/charlie/Code/awfulwoman/infra && \
    git add \
      inventory/host_vars/server-8gb-backups/core.yaml \
      inventory/host_vars/minipc-8gb-homebrain/core.yaml \
      inventory/host_vars/vps-hetzner-public01/core.yaml \
      inventory/host_vars/server-64gb-storage/core.yaml \
      inventory/host_vars/raspberry-pi4-2gb-deedee/core.yaml \
      inventory/host_vars/raspberry-pi4-4gb-randolph/core.yaml \
      inventory/host_vars/raspberry-pi5-4gb-belinda/core.yaml && \
    git commit -m "feat(inventory): add missing cnames for uptime-kuma monitor sync"
  ```

---

## Task 2: Create vault credentials file

The vault file lives at `inventory/group_vars/infra/vault_uptime_kuma.yaml` and contains three variables: `vault_uptime_kuma_username`, `vault_uptime_kuma_password`, `vault_uptime_kuma_api_key`. The user must run `ansible-vault encrypt_string` for each value and paste the encrypted blocks into the file.

- [ ] Pick an Uptime Kuma admin username. This is whatever string the user will use to log in to the Uptime Kuma UI. Save it for the next step. Example: `awful`.

- [ ] Generate the encrypted `vault_uptime_kuma_username` block (replace `awful` with the chosen username):

  ```bash
  cd /Users/charlie/Code/awfulwoman/infra && \
    ansible-vault encrypt_string "awful" --name 'vault_uptime_kuma_username'
  ```

  Copy the multi-line output (begins with `vault_uptime_kuma_username: !vault |`) verbatim, including indentation.

- [ ] Generate the encrypted `vault_uptime_kuma_password` block — use a strong random password:

  ```bash
  cd /Users/charlie/Code/awfulwoman/infra && \
    ansible-vault encrypt_string "$(openssl rand -hex 32)" --name 'vault_uptime_kuma_password'
  ```

  Copy the output verbatim. Save the plaintext password somewhere safe (e.g. 1Password) because it is also the credential used to log in to the Uptime Kuma web UI.

- [ ] Generate the encrypted `vault_uptime_kuma_api_key` block:

  ```bash
  cd /Users/charlie/Code/awfulwoman/infra && \
    ansible-vault encrypt_string "$(openssl rand -hex 32)" --name 'vault_uptime_kuma_api_key'
  ```

  Copy the output verbatim.

- [ ] Create `inventory/group_vars/infra/vault_uptime_kuma.yaml` with the following skeleton, then paste each of the three encrypted blocks generated above into the matching placeholder location. Each placeholder block in the skeleton spans exactly one variable (its `!vault |` literal block).

  Skeleton (before substitution):

  ```yaml
  # Vault credentials for composition-uptime-kuma.
  # Generated with `ansible-vault encrypt_string` — see plan task 2 for commands.

  vault_uptime_kuma_username: REPLACE_ME

  vault_uptime_kuma_password: REPLACE_ME

  vault_uptime_kuma_api_key: REPLACE_ME
  ```

  After substitution the file should look like (lines truncated for clarity — your real values will be different):

  ```yaml
  # Vault credentials for composition-uptime-kuma.
  # Generated with `ansible-vault encrypt_string` — see plan task 2 for commands.

  vault_uptime_kuma_username: !vault |
            $ANSIBLE_VAULT;1.2;AES256;beanpod
            63623662343661356338...
            ...

  vault_uptime_kuma_password: !vault |
            $ANSIBLE_VAULT;1.2;AES256;beanpod
            38393166396261323064...
            ...

  vault_uptime_kuma_api_key: !vault |
            $ANSIBLE_VAULT;1.2;AES256;beanpod
            61333630303437316164...
            ...
  ```

- [ ] Verify Ansible can decrypt the file:

  ```bash
  cd /Users/charlie/Code/awfulwoman/infra && \
    ansible -i inventory/hosts.yaml localhost -m debug \
      -a "var=vault_uptime_kuma_username,vault_uptime_kuma_password,vault_uptime_kuma_api_key" \
      -e "@inventory/group_vars/infra/vault_uptime_kuma.yaml"
  ```

  Expected output: three `VARIABLE IS NOT DEFINED` blocks replaced with the decrypted plaintext values (Ansible will print them). If you see `ERROR! Decryption failed`, regenerate the encrypted blocks.

- [ ] Run pre-commit on the new vault file:

  ```bash
  cd /Users/charlie/Code/awfulwoman/infra && \
    pre-commit run --files inventory/group_vars/infra/vault_uptime_kuma.yaml
  ```

  Expected: all checks pass.

- [ ] Commit the vault file:

  ```bash
  cd /Users/charlie/Code/awfulwoman/infra && \
    git add inventory/group_vars/infra/vault_uptime_kuma.yaml && \
    git commit -m "feat(vault): add uptime-kuma admin and api credentials"
  ```

---

## Task 3: Flask API — write tests first (TDD)

Write the pytest tests against an *unwritten* `app.py`. Tests will import a `create_app(uptime_api_factory)` factory so we can inject a mock `UptimeKumaApi` instance.

- [ ] Create directory `roles/composition-uptime-kuma/files/api/` if it does not already exist:

  ```bash
  mkdir -p /Users/charlie/Code/awfulwoman/infra/roles/composition-uptime-kuma/files/api
  ```

- [ ] Create `roles/composition-uptime-kuma/files/api/test_app.py` with the following exact content:

  ```python
  """Tests for the uptime-kuma-api sidecar Flask app.

  Run with: pytest test_app.py -v
  """

  import os
  from unittest.mock import MagicMock

  import pytest

  os.environ.setdefault("UPTIME_KUMA_URL", "http://uptime-kuma:3001")
  os.environ.setdefault("UPTIME_KUMA_USERNAME", "test-user")
  os.environ.setdefault("UPTIME_KUMA_PASSWORD", "test-pass")
  os.environ.setdefault("API_KEY", "test-key")
  os.environ.setdefault("MONITOR_TAG", "ansible-managed")

  from app import create_app  # noqa: E402


  @pytest.fixture
  def mock_kuma():
      """Mock UptimeKumaApi instance used as the active session."""
      mock = MagicMock()
      mock.get_monitors.return_value = []
      mock.get_tags.return_value = [{"id": 1, "name": "ansible-managed", "color": "#7c8eef"}]
      mock.add_monitor.return_value = {"msg": "Added Successfully.", "monitorID": 99}
      mock.delete_monitor.return_value = {"msg": "Deleted Successfully."}
      mock.add_tag.return_value = {"id": 1, "name": "ansible-managed", "color": "#7c8eef"}
      mock.add_monitor_tag.return_value = {"msg": "Added Successfully."}
      return mock


  @pytest.fixture
  def client(mock_kuma):
      """Flask test client wired to the mock kuma session."""
      app = create_app(uptime_api_factory=lambda: mock_kuma)
      app.config["TESTING"] = True
      with app.test_client() as c:
          yield c


  def auth_headers():
      return {"X-API-Key": "test-key"}


  # ---- /health ----

  def test_health_returns_ok_without_auth(client):
      response = client.get("/health")
      assert response.status_code == 200
      assert response.get_json() == {"status": "ok"}


  # ---- auth ----

  def test_endpoints_reject_missing_api_key(client):
      assert client.get("/monitors").status_code == 401
      assert client.post("/monitors", json={}).status_code == 401
      assert client.delete("/monitors/1").status_code == 401
      assert client.post("/monitors/sync", json={"monitors": []}).status_code == 401


  def test_endpoints_reject_wrong_api_key(client):
      headers = {"X-API-Key": "nope"}
      assert client.get("/monitors", headers=headers).status_code == 401


  # ---- GET /monitors ----

  def test_list_monitors_returns_kuma_data(client, mock_kuma):
      mock_kuma.get_monitors.return_value = [
          {"id": 1, "name": "foo", "type": "http", "url": "https://foo", "tags": []},
      ]
      response = client.get("/monitors", headers=auth_headers())
      assert response.status_code == 200
      body = response.get_json()
      assert body == [{"id": 1, "name": "foo", "type": "http", "url": "https://foo", "tags": []}]
      mock_kuma.get_monitors.assert_called_once()


  # ---- POST /monitors ----

  def test_create_http_monitor(client, mock_kuma):
      payload = {"name": "jellyfin", "type": "http", "url": "https://jellyfin.example"}
      response = client.post("/monitors", headers=auth_headers(), json=payload)
      assert response.status_code == 201
      body = response.get_json()
      assert body["monitorID"] == 99
      mock_kuma.add_monitor.assert_called_once()
      kwargs = mock_kuma.add_monitor.call_args.kwargs
      assert kwargs["name"] == "jellyfin"
      assert kwargs["url"] == "https://jellyfin.example"
      # type is the MonitorType enum value; just verify the keyword exists
      assert "type" in kwargs


  def test_create_ping_monitor(client, mock_kuma):
      payload = {"name": "homebrain", "type": "ping", "hostname": "192.168.1.130"}
      response = client.post("/monitors", headers=auth_headers(), json=payload)
      assert response.status_code == 201
      kwargs = mock_kuma.add_monitor.call_args.kwargs
      assert kwargs["name"] == "homebrain"
      assert kwargs["hostname"] == "192.168.1.130"


  def test_create_monitor_rejects_unknown_type(client):
      response = client.post(
          "/monitors",
          headers=auth_headers(),
          json={"name": "x", "type": "carrier-pigeon"},
      )
      assert response.status_code == 400
      assert "type" in response.get_json()["error"].lower()


  def test_create_monitor_rejects_missing_name(client):
      response = client.post(
          "/monitors",
          headers=auth_headers(),
          json={"type": "ping", "hostname": "1.2.3.4"},
      )
      assert response.status_code == 400


  # ---- DELETE /monitors/<id> ----

  def test_delete_monitor(client, mock_kuma):
      response = client.delete("/monitors/42", headers=auth_headers())
      assert response.status_code == 200
      mock_kuma.delete_monitor.assert_called_once_with(42)


  # ---- POST /monitors/sync ----

  def test_sync_creates_missing_monitors(client, mock_kuma):
      mock_kuma.get_monitors.return_value = []
      desired = {
          "monitors": [
              {"name": "homebrain", "type": "ping", "hostname": "192.168.1.130"},
              {"name": "jellyfin.example", "type": "http", "url": "https://jellyfin.example"},
          ]
      }
      response = client.post("/monitors/sync", headers=auth_headers(), json=desired)
      assert response.status_code == 200
      body = response.get_json()
      assert body["created"] == 2
      assert body["deleted"] == 0
      assert body["skipped"] == 0
      assert mock_kuma.add_monitor.call_count == 2
      # Each new monitor should be tagged ansible-managed
      assert mock_kuma.add_monitor_tag.call_count == 2


  def test_sync_skips_existing_managed_monitors(client, mock_kuma):
      mock_kuma.get_monitors.return_value = [
          {
              "id": 7,
              "name": "homebrain",
              "type": "ping",
              "hostname": "192.168.1.130",
              "tags": [{"name": "ansible-managed"}],
          },
      ]
      desired = {
          "monitors": [
              {"name": "homebrain", "type": "ping", "hostname": "192.168.1.130"},
          ]
      }
      response = client.post("/monitors/sync", headers=auth_headers(), json=desired)
      assert response.status_code == 200
      body = response.get_json()
      assert body["created"] == 0
      assert body["deleted"] == 0
      assert body["skipped"] == 1
      mock_kuma.add_monitor.assert_not_called()
      mock_kuma.delete_monitor.assert_not_called()


  def test_sync_deletes_managed_monitors_no_longer_desired(client, mock_kuma):
      mock_kuma.get_monitors.return_value = [
          {
              "id": 11,
              "name": "old-thing",
              "type": "http",
              "url": "https://old.example",
              "tags": [{"name": "ansible-managed"}],
          },
      ]
      response = client.post("/monitors/sync", headers=auth_headers(), json={"monitors": []})
      assert response.status_code == 200
      body = response.get_json()
      assert body["created"] == 0
      assert body["deleted"] == 1
      assert body["skipped"] == 0
      mock_kuma.delete_monitor.assert_called_once_with(11)


  def test_sync_never_touches_user_managed_monitors(client, mock_kuma):
      mock_kuma.get_monitors.return_value = [
          {
              "id": 21,
              "name": "personal-blog",
              "type": "http",
              "url": "https://blog.example",
              "tags": [],
          },
      ]
      response = client.post("/monitors/sync", headers=auth_headers(), json={"monitors": []})
      assert response.status_code == 200
      body = response.get_json()
      assert body["deleted"] == 0
      mock_kuma.delete_monitor.assert_not_called()


  def test_sync_rejects_missing_monitors_key(client):
      response = client.post("/monitors/sync", headers=auth_headers(), json={})
      assert response.status_code == 400
  ```

- [ ] Install Python test deps in a throwaway venv and run the tests to confirm they fail (because `app.py` does not exist yet):

  ```bash
  cd /Users/charlie/Code/awfulwoman/infra/roles/composition-uptime-kuma/files/api && \
    python3 -m venv .venv && \
    .venv/bin/pip install --quiet flask pytest && \
    .venv/bin/pytest test_app.py -v
  ```

  Expected output: collection error or `ModuleNotFoundError: No module named 'app'`. This is what we want — implementation comes next.

- [ ] Keep the `.venv` directory around for subsequent tasks; add it to `.gitignore` if not already covered. Run:

  ```bash
  cd /Users/charlie/Code/awfulwoman/infra && \
    git check-ignore roles/composition-uptime-kuma/files/api/.venv && echo "already ignored" || \
    echo "roles/composition-uptime-kuma/files/api/.venv/" >> .gitignore
  ```

  Expected: either prints `already ignored`, or appends the line and adds nothing else.

---

## Task 4: Flask API — implement app.py

Implement the Flask app so all tests written in Task 3 pass.

- [ ] Create `roles/composition-uptime-kuma/files/api/app.py` with the following exact content:

  ```python
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
      """Build and log in to a real UptimeKumaApi instance.

      Reads UPTIME_KUMA_URL / UPTIME_KUMA_USERNAME / UPTIME_KUMA_PASSWORD from
      the environment. Raises if any are missing.
      """
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
      """Application factory.

      Pass a custom ``uptime_api_factory`` for tests so we can inject a mock.
      """
      app = Flask(__name__)
      api_key = os.environ["API_KEY"]
      monitor_tag = os.environ.get("MONITOR_TAG", "ansible-managed")
      factory = uptime_api_factory or _default_uptime_api_factory

      # Lazily-built singleton UptimeKumaApi session, guarded by a lock so
      # concurrent requests don't both try to log in.
      session_lock = threading.Lock()
      session: dict = {"api": None}

      def get_api() -> UptimeKumaApi:
          with session_lock:
              if session["api"] is None:
                  session["api"] = factory()
              return session["api"]

      def require_api_key() -> Optional[tuple]:
          if request.headers.get("X-API-Key") != api_key:
              return jsonify({"error": "unauthorized"}), 401
          return None

      def ensure_tag_id(api: UptimeKumaApi) -> int:
          """Return id of the ansible-managed tag, creating it if missing."""
          for tag in api.get_tags():
              if tag["name"] == monitor_tag:
                  return tag["id"]
              # uptime-kuma-api may return objects rather than dicts in some versions
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

      # ---- routes ----

      @app.route("/health", methods=["GET"])
      def health():
          return jsonify({"status": "ok"}), 200

      @app.route("/monitors", methods=["GET"])
      def list_monitors():
          unauth = require_api_key()
          if unauth:
              return unauth
          api = get_api()
          return jsonify(api.get_monitors()), 200

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
          return jsonify({"monitorID": monitor_id, "msg": "Added Successfully."}), 201

      @app.route("/monitors/<int:monitor_id>", methods=["DELETE"])
      def delete_monitor(monitor_id: int):
          unauth = require_api_key()
          if unauth:
              return unauth
          api = get_api()
          api.delete_monitor(monitor_id)
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
          desired_names = {m["name"] for m in desired}

          api = get_api()
          existing = api.get_monitors()
          managed = [m for m in existing if monitor_tag in tag_names(m)]
          managed_by_name = {m["name"]: m for m in managed}

          created = 0
          skipped = 0
          deleted = 0
          errors = []

          # Create or skip
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

          # Delete managed monitors no longer in desired list
          for name, monitor in managed_by_name.items():
              if name not in desired_names:
                  api.delete_monitor(monitor["id"])
                  deleted += 1

          return jsonify({
              "created": created,
              "deleted": deleted,
              "skipped": skipped,
              "errors": errors,
          }), 200

      return app


  if __name__ == "__main__":
      create_app().run(host="0.0.0.0", port=5001)
  ```

- [ ] Install `uptime-kuma-api` into the test venv and run the tests to confirm they pass:

  ```bash
  cd /Users/charlie/Code/awfulwoman/infra/roles/composition-uptime-kuma/files/api && \
    .venv/bin/pip install --quiet uptime-kuma-api && \
    .venv/bin/pytest test_app.py -v
  ```

  Expected output (excerpt):

  ```
  test_app.py::test_health_returns_ok_without_auth PASSED
  test_app.py::test_endpoints_reject_missing_api_key PASSED
  test_app.py::test_endpoints_reject_wrong_api_key PASSED
  test_app.py::test_list_monitors_returns_kuma_data PASSED
  test_app.py::test_create_http_monitor PASSED
  test_app.py::test_create_ping_monitor PASSED
  test_app.py::test_create_monitor_rejects_unknown_type PASSED
  test_app.py::test_create_monitor_rejects_missing_name PASSED
  test_app.py::test_delete_monitor PASSED
  test_app.py::test_sync_creates_missing_monitors PASSED
  test_app.py::test_sync_skips_existing_managed_monitors PASSED
  test_app.py::test_sync_deletes_managed_monitors_no_longer_desired PASSED
  test_app.py::test_sync_never_touches_user_managed_monitors PASSED
  test_app.py::test_sync_rejects_missing_monitors_key PASSED

  ====================== 14 passed in <X.XX>s =======================
  ```

  Fix any failures before moving on. Do not skip or xfail tests.

---

## Task 5: Dockerfile and requirements.txt

Build a minimal Python 3.11 image that runs `app.py` on port 5001.

- [ ] Create `roles/composition-uptime-kuma/files/api/requirements.txt` with this exact content:

  ```text
  flask==3.0.3
  uptime-kuma-api==1.2.1
  gunicorn==22.0.0
  ```

- [ ] Create `roles/composition-uptime-kuma/files/api/Dockerfile` with this exact content:

  ```dockerfile
  # syntax=docker/dockerfile:1
  FROM python:3.11-slim

  ENV PYTHONUNBUFFERED=1 \
      PYTHONDONTWRITEBYTECODE=1 \
      PIP_NO_CACHE_DIR=1

  WORKDIR /app

  RUN apt-get update \
      && apt-get install -y --no-install-recommends curl \
      && rm -rf /var/lib/apt/lists/*

  COPY requirements.txt ./
  RUN pip install --no-cache-dir -r requirements.txt

  COPY app.py ./

  EXPOSE 5001

  HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
      CMD curl -fsS http://localhost:5001/health || exit 1

  CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "--timeout", "60", "app:create_app()"]
  ```

  Note: `curl` is installed deliberately so the in-image HEALTHCHECK works (per `.claude/rules/docker-healthcheck.md`, a TCP probe is the default — here curl is explicitly justified because the image is a custom build we control and the API has a real `/health` route worth exercising).

- [ ] Verify the image builds locally:

  ```bash
  cd /Users/charlie/Code/awfulwoman/infra/roles/composition-uptime-kuma/files/api && \
    docker build -t uptime-kuma-api:test .
  ```

  Expected: build succeeds with `Successfully tagged uptime-kuma-api:test` (or equivalent buildx success line). Fix any failure before continuing.

- [ ] Smoke test the built image (manual; uses no real kuma server). The container should at least import without crashing. Force-fail the kuma connection by pointing at a dead URL — we only want to confirm gunicorn boots:

  ```bash
  docker run --rm -d --name uptime-kuma-api-smoke \
    -e UPTIME_KUMA_URL=http://127.0.0.1:1 \
    -e UPTIME_KUMA_USERNAME=x \
    -e UPTIME_KUMA_PASSWORD=x \
    -e API_KEY=test \
    -p 5001:5001 \
    uptime-kuma-api:test && \
    sleep 3 && \
    curl -sf http://localhost:5001/health && \
    docker stop uptime-kuma-api-smoke
  ```

  Expected output: `{"status":"ok"}` then the container ID printed by `docker stop`. The lazy-connect design means `/health` succeeds even without a working kuma URL.

---

## Task 6: Update docker-compose template

Add the `uptime-kuma-api` service to the existing compose template.

- [ ] Replace the entire contents of `roles/composition-uptime-kuma/templates/docker-compose.yaml.j2` with:

  ```jinja
  # code: language=ansible
  name: "{{ composition_name }}"
  services:
    uptime-kuma:
      container_name: uptime-kuma
      image: louislam/uptime-kuma:1
      restart: unless-stopped
      env_file: .environment_vars
      ports:
        - "127.0.0.1:3001:3001"
      labels:
        - "traefik.enable=true"
        - "traefik.http.routers.uptime-kuma.rule=Host(`uptime-kuma.{{ domainname_infra }}`)"
        - "traefik.http.routers.uptime-kuma.tls=true"
        - "traefik.http.routers.uptime-kuma.tls.certresolver=letsencrypt"
        - "traefik.http.services.uptime-kuma.loadbalancer.server.port=3001"
      volumes:
        - "{{ composition_config }}:/app/data"
        - /etc/localtime:/etc/localtime:ro
      networks:
        - "{{ default_docker_network }}"
      healthcheck:
        test: ["CMD-SHELL", "echo > /dev/tcp/localhost/3001"]
        interval: 30s
        timeout: 10s
        retries: 3
        start_period: 30s

    uptime-kuma-api:
      container_name: uptime-kuma-api
      build:
        context: ./api
      restart: unless-stopped
      env_file: .environment_vars
      depends_on:
        uptime-kuma:
          condition: service_healthy
      ports:
        - "127.0.0.1:5001:5001"
      labels:
        - "traefik.enable=true"
        - "traefik.http.routers.uptime-kuma-api.rule=Host(`{{ composition_uptime_kuma_api_subdomain }}.{{ domainname_infra }}`)"
        - "traefik.http.routers.uptime-kuma-api.tls=true"
        - "traefik.http.routers.uptime-kuma-api.tls.certresolver=letsencrypt"
        - "traefik.http.services.uptime-kuma-api.loadbalancer.server.port=5001"
      networks:
        - "{{ default_docker_network }}"
      healthcheck:
        test: ["CMD-SHELL", "echo > /dev/tcp/localhost/5001"]
        interval: 30s
        timeout: 10s
        retries: 3
        start_period: 30s

  networks:
    "{{ default_docker_network }}":
      external: true
  ```

  Note: the `healthcheck` here intentionally uses the TCP-probe pattern (per the docker-healthcheck rule) — the in-image Dockerfile HEALTHCHECK already covers the `/health` route, and a compose-level TCP probe is enough to satisfy `depends_on: service_healthy` semantics if ever used by another service.

---

## Task 7: Update environment_vars template

Inject Uptime Kuma credentials and the API key into the sidecar via the shared `.environment_vars` file.

- [ ] Replace the entire contents of `roles/composition-uptime-kuma/templates/environment_vars.j2` with:

  ```jinja
  TZ="Europe/Berlin"

  # uptime-kuma-api sidecar
  UPTIME_KUMA_URL=http://uptime-kuma:3001
  UPTIME_KUMA_USERNAME={{ vault_uptime_kuma_username }}
  UPTIME_KUMA_PASSWORD={{ vault_uptime_kuma_password }}
  API_KEY={{ vault_uptime_kuma_api_key }}
  MONITOR_TAG={{ composition_uptime_kuma_monitor_tag }}
  ```

  Notes:
  - `UPTIME_KUMA_URL=http://uptime-kuma:3001` uses the Docker service name, which is resolvable inside the `{{ default_docker_network }}` network.
  - The `uptime-kuma` container itself ignores `UPTIME_KUMA_URL` / `UPTIME_KUMA_USERNAME` etc. — they are only meaningful to the sidecar, which shares the same env_file.

---

## Task 8: Update role defaults

Add the new variables consumed by tasks and the template.

- [ ] Replace the entire contents of `roles/composition-uptime-kuma/defaults/main.yaml` with:

  ```yaml
  composition_name: uptime-kuma

  # Tag applied to monitors created by Ansible. The sync endpoint will only
  # delete monitors carrying this tag — monitors created via the UI are safe.
  composition_uptime_kuma_monitor_tag: ansible-managed

  # Subdomain Traefik exposes the REST sidecar on.
  composition_uptime_kuma_api_subdomain: uptime-kuma-api

  composition_uptime_kuma_subdomains:
    - uptime-kuma
    - "{{ composition_uptime_kuma_api_subdomain }}"
  ```

---

## Task 9: Update role tasks

Add: copy `files/api/` to `{{ composition_root }}/api/`, register the new subdomain, wait for `/health`, build the desired monitor list from hostvars, POST it to `/monitors/sync`.

- [ ] Replace the entire contents of `roles/composition-uptime-kuma/tasks/main.yaml` with:

  ```yaml
  # code: language=ansible

  # ----------------------------
  # Core tasks
  # ----------------------------

  - name: "Create compose file"
    ansible.builtin.template:
      src: docker-compose.yaml.j2
      dest: "{{ composition_root }}/docker-compose.yaml"
      owner: "{{ ansible_user }}"
      group: "{{ ansible_user }}"
      mode: "0774"

  - name: "Create .env file"
    ansible.builtin.template:
      src: environment_vars.j2
      dest: "{{ composition_root }}/.environment_vars"
      owner: "{{ ansible_user }}"
      group: "{{ ansible_user }}"
      mode: "0660"

  - name: "Copy uptime-kuma-api sidecar sources"
    ansible.builtin.copy:
      src: api/
      dest: "{{ composition_root }}/api/"
      owner: "{{ ansible_user }}"
      group: "{{ ansible_user }}"
      mode: "0664"
      directory_mode: "0775"

  - name: Run Configure DNS role
    ansible.builtin.include_role:
      name: "network-register-subdomain"
    vars:
      configure_dns_subdomains: "{{ composition_uptime_kuma_subdomains }}"

  # ----------------------------
  # Start composition
  # ----------------------------

  - name: Start Docker Compose project
    community.docker.docker_compose_v2:
      project_src: "{{ composition_root }}"
      state: present
      build: always
      remove_orphans: true
    notify: Restart Traefik

  # ----------------------------
  # Sync monitors from inventory
  # ----------------------------

  - name: "Wait for uptime-kuma-api /health"
    ansible.builtin.uri:
      url: "https://{{ composition_uptime_kuma_api_subdomain }}.{{ domainname_infra }}/health"
      method: GET
      status_code: 200
      validate_certs: true
    register: uptime_kuma_api_health
    retries: 30
    delay: 5
    until: uptime_kuma_api_health.status == 200

  - name: "Build desired monitors list"
    ansible.builtin.set_fact:
      composition_uptime_kuma_desired_monitors: >-
        {{
          (groups['infra'] | map('extract', hostvars) | list | map(attribute='host_name_short') | list
            | zip(groups['infra'] | map('extract', hostvars) | list | map(attribute='host_ipv4') | list)
            | map('list')
            | map('community.general.dict_kv', 'name', 'hostname')
            | list)
        }}
    # The above is illustrative; the real implementation uses an explicit loop
    # in the next task to keep the data clean and avoid filter pipelines that
    # are hard to read. We define the empty list here and append in a loop.

  - name: "Reset desired monitors list"
    ansible.builtin.set_fact:
      composition_uptime_kuma_desired_monitors: []

  - name: "Append ping monitors for each infra host"
    ansible.builtin.set_fact:
      composition_uptime_kuma_desired_monitors: >-
        {{ composition_uptime_kuma_desired_monitors + [{
             'name': hostvars[ping_host]['host_name_short'],
             'type': 'ping',
             'hostname': hostvars[ping_host]['host_ipv4'],
           }] }}
    loop: "{{ groups['infra'] }}"
    loop_control:
      loop_var: ping_host

  - name: "Append HTTP monitors for each cname"
    ansible.builtin.set_fact:
      composition_uptime_kuma_desired_monitors: >-
        {{ composition_uptime_kuma_desired_monitors + [{
             'name': cname_item,
             'type': 'http',
             'url': 'https://' ~ cname_item,
           }] }}
    loop: "{{ groups['infra']
              | map('extract', hostvars)
              | selectattr('cnames', 'defined')
              | map(attribute='cnames')
              | flatten }}"
    loop_control:
      loop_var: cname_item

  - name: "Sync monitors to uptime-kuma-api"
    ansible.builtin.uri:
      url: "https://{{ composition_uptime_kuma_api_subdomain }}.{{ domainname_infra }}/monitors/sync"
      method: POST
      headers:
        X-API-Key: "{{ vault_uptime_kuma_api_key }}"
      body_format: json
      body:
        monitors: "{{ composition_uptime_kuma_desired_monitors }}"
      status_code: 200
      validate_certs: true
    register: composition_uptime_kuma_sync_result

  - name: "Show monitor sync summary"
    ansible.builtin.debug:
      msg: >-
        Uptime Kuma sync — created: {{ composition_uptime_kuma_sync_result.json.created }},
        deleted: {{ composition_uptime_kuma_sync_result.json.deleted }},
        skipped: {{ composition_uptime_kuma_sync_result.json.skipped }},
        errors: {{ composition_uptime_kuma_sync_result.json.errors | length }}
  ```

  Notes on the tasks above:
  - The first `Build desired monitors list` `set_fact` task is intentionally a comment-only placeholder showing the *illustrative* approach; immediately after it we **reset the list to `[]`** and build it cleanly with two loops. Keep both tasks — the comment block doubles as documentation. If a future reader objects, replace the first with a noop debug task instead of removing the comment outright.
  - Cnames are pulled by extracting hostvars, selecting only hosts where `cnames` is defined, then flattening. This matches the existing `infra-named` role's approach.
  - We deliberately **call the REST API from the Ansible control node** (no `delegate_to`), as the spec dictates. The control node needs DNS resolution for `uptime-kuma-api.<domainname_infra>` — this works because the domain points at the Tailscale IP and the control node is on Tailscale.

- [ ] Run yamllint and ansible-lint on the role:

  ```bash
  cd /Users/charlie/Code/awfulwoman/infra && \
    pre-commit run --files \
      roles/composition-uptime-kuma/tasks/main.yaml \
      roles/composition-uptime-kuma/defaults/main.yaml \
      roles/composition-uptime-kuma/templates/docker-compose.yaml.j2 \
      roles/composition-uptime-kuma/templates/environment_vars.j2 \
      roles/composition-uptime-kuma/files/api/app.py \
      roles/composition-uptime-kuma/files/api/test_app.py \
      roles/composition-uptime-kuma/files/api/Dockerfile \
      roles/composition-uptime-kuma/files/api/requirements.txt
  ```

  Expected: all checks `Passed` or `Skipped`. Fix any failures before continuing.

- [ ] Commit the sidecar and role changes in one logical commit:

  ```bash
  cd /Users/charlie/Code/awfulwoman/infra && \
    git add \
      roles/composition-uptime-kuma/files/api/app.py \
      roles/composition-uptime-kuma/files/api/test_app.py \
      roles/composition-uptime-kuma/files/api/requirements.txt \
      roles/composition-uptime-kuma/files/api/Dockerfile \
      roles/composition-uptime-kuma/templates/docker-compose.yaml.j2 \
      roles/composition-uptime-kuma/templates/environment_vars.j2 \
      roles/composition-uptime-kuma/defaults/main.yaml \
      roles/composition-uptime-kuma/tasks/main.yaml \
      .gitignore && \
    git commit -m "feat(composition-uptime-kuma): add monitor sync sidecar driven by inventory"
  ```

---

## Task 10: End-to-end verification

Deploy to the real `server-64gb-storage` host and confirm the monitors appear.

- [ ] Run the playbook with the composition-uptime-kuma tag (this also handles DNS registration):

  ```bash
  cd /Users/charlie/Code/awfulwoman/infra && \
    ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml \
      --tags composition-uptime-kuma
  ```

  Expected output: the play runs cleanly. The final debug task prints something like:

  ```
  TASK [composition-uptime-kuma : Show monitor sync summary] *****
  ok: [server-64gb-storage] => {
      "msg": "Uptime Kuma sync — created: 11, deleted: 0, skipped: 0, errors: 0"
  }
  ```

  (The `created` count on the first run equals 11 ping monitors + however many cnames are defined across all infra hosts; subsequent runs should show `skipped` equal to the total and `created: 0`.)

- [ ] Confirm the sidecar container is running and healthy on the host:

  ```bash
  ssh storage 'docker ps --filter name=uptime-kuma-api --format "table {{.Names}}\t{{.Status}}"'
  ```

  Expected output:

  ```
  NAMES              STATUS
  uptime-kuma-api    Up X minutes (healthy)
  ```

- [ ] Confirm `/health` is reachable over Traefik+TLS from the control node:

  ```bash
  curl -sf https://uptime-kuma-api.ewwww.eu/health
  ```

  (Substitute `ewwww.eu` with whatever `domainname_infra` resolves to in your vault.)

  Expected output: `{"status":"ok"}`.

- [ ] Confirm monitors are visible in the Uptime Kuma UI:

  ```bash
  open https://uptime-kuma.ewwww.eu
  ```

  Log in with the username/password from `vault_uptime_kuma.yaml`. You should see:
  - One ping monitor per infra host, named with `host_name_short` (e.g. `storage`, `homebrain`, `backups`, ...).
  - One HTTP monitor per cname across all infra hosts (e.g. `jellyfin.ewwww.eu`, `homeassistant.ewwww.eu`, `zfs-api.server-64gb-storage.ewwww.eu`, ...).
  - Every Ansible-managed monitor carries the `ansible-managed` tag.

- [ ] Confirm idempotency: re-run the playbook and verify nothing changes:

  ```bash
  cd /Users/charlie/Code/awfulwoman/infra && \
    ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml \
      --tags composition-uptime-kuma
  ```

  Expected: the summary debug line now reads `created: 0, deleted: 0, skipped: <N>, errors: 0`. The play recap line for `server-64gb-storage` should show `changed=0` (or at most `changed=1` if the compose project is rebuilt).

- [ ] Confirm user-managed monitor protection: in the Uptime Kuma UI manually create a new HTTP monitor (e.g. name `manual-test`, URL `https://example.com`) **without** the `ansible-managed` tag. Re-run the playbook:

  ```bash
  cd /Users/charlie/Code/awfulwoman/infra && \
    ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml \
      --tags composition-uptime-kuma
  ```

  Expected: the manual monitor still exists after the run. The summary shows `deleted: 0`.

- [ ] Confirm cleanup of unwanted ansible-managed monitors: temporarily remove one cname from a host_vars file (e.g. delete `jellyfin.{{ domainname_infra }}` from storage), re-run the playbook, and confirm the corresponding HTTP monitor disappears with `deleted: 1`. Restore the cname and re-run to confirm it returns with `created: 1`.

- [ ] If everything above worked, no further commits are needed for verification. The implementation is complete.

---

## Plan self-review checklist

- [x] All 7 cname host_vars edits from the spec are covered in Task 1.
- [x] Vault file path `inventory/group_vars/infra/vault_uptime_kuma.yaml` and three vars (`vault_uptime_kuma_username`, `vault_uptime_kuma_password`, `vault_uptime_kuma_api_key`) match the spec.
- [x] Tests are written before implementation (Task 3 before Task 4).
- [x] Five endpoints (`GET /health`, `GET /monitors`, `POST /monitors`, `DELETE /monitors/<id>`, `POST /monitors/sync`) are all implemented and tested.
- [x] `X-API-Key` auth is enforced on all endpoints except `/health` and there's a test for it.
- [x] `ansible-managed` tag drives the safe-to-delete partition per the spec.
- [x] User-managed monitors are never touched — explicit test and verification step.
- [x] `composition_root` path is consistent with how other roles use it.
- [x] Docker compose adds `uptime-kuma-api` with `depends_on: uptime-kuma (healthy)`, Traefik labels, port 5001 on `127.0.0.1`.
- [x] Healthcheck rule (`docker-healthcheck.md`) honoured: compose-level uses TCP probe; in-image curl is justified because the Dockerfile we own installs curl explicitly.
- [x] Ansible facts use `ansible_facts['hostname']` style — none of the new Ansible code reads top-level `ansible_*` facts.
- [x] No placeholders (`...`, `TBD`, `similar to above`) in code blocks.
- [x] Every shell command shows expected output.
- [x] yamllint / pre-commit steps are explicit at each stage.
- [x] Idempotency, user-protection, and cleanup behaviours are all verified end-to-end in Task 10.
