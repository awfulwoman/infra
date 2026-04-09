# composition-open-webui Design Spec

**Date:** 2026-04-09

## Overview

Deploy Open WebUI as a Docker Compose composition on host-storage, wired to the Ollama instance running on Malcolm (Mac Mini M4) at `http://192.168.1.150:11434`.

## Role Structure

New role: `ansible/roles/composition-open-webui/`

```
composition-open-webui/
  defaults/main.yaml
  meta/main.yaml
  tasks/main.yaml
  templates/
    docker-compose.yaml.j2
    environment_vars.j2
```

Follows the established `composition-*` pattern used by all other Docker Compose roles in this repo.

## Defaults

```yaml
composition_name: open-webui
composition_open_webui_ollama_base_url: ""
```

`composition_open_webui_ollama_base_url` is left empty by default and must be set per-host in host_vars. This ensures the role is reusable across hosts pointing to different Ollama instances.

## Meta

Declares `composition-common` as a dependency (as all composition roles do), which resolves `composition_root` and `composition_config` paths under `/fastpool/compositions/open-webui/`.

## Tasks

1. Template `docker-compose.yaml.j2` → `{{ composition_root }}/docker-compose.yaml`
2. Template `environment_vars.j2` → `{{ composition_root }}/.environment_vars`
3. Register DNS subdomain `chat` via `network-register-subdomain`
4. Start Docker Compose project via `community.docker.docker_compose_v2`

## Docker Compose

- **Image:** `ghcr.io/open-webui/open-webui:main`
- **Internal port:** `8080`
- **Restart policy:** `unless-stopped`
- **Volume:** `{{ composition_config }}/data:/app/backend/data` (SQLite database, uploaded files)
- **Network:** `{{ default_docker_network }}` (external, shared with Traefik)
- **Traefik labels:**
  - Route `chat.{{ domain_name }}` → port 8080
  - TLS via `letsencrypt` certresolver

## Environment Variables

```
TZ="Europe/Berlin"
OLLAMA_BASE_URL="{{ composition_open_webui_ollama_base_url }}"
WEBUI_AUTH=False
```

`WEBUI_AUTH=False` disables the login screen for open access on the trusted Tailscale network. This can be re-enabled later by setting it to `True`.

## Host Configuration (host-storage)

Add to `ansible/inventory/host_vars/host-storage/core.yaml`:

```yaml
composition_open_webui_ollama_base_url: "http://192.168.1.150:11434"
```

Add to the `cnames` list:

```yaml
- chat.{{ domain_name }}
```

## Playbook

Add `composition-open-webui` to `ansible/playbooks/baremetal/host-storage/compositions.yaml`.

## Out of Scope

- GPU passthrough (Open WebUI is UI-only; inference runs on Malcolm)
- Image pipeline tools or RAG configuration
- Re-enabling auth (can be done by setting `WEBUI_AUTH=True` in host_vars later)
