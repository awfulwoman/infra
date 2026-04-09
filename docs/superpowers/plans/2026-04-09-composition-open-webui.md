# composition-open-webui Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create an Ansible role that deploys Open WebUI as a Docker Compose composition on host-storage, connected to Ollama on Malcolm.

**Architecture:** Standard `composition-*` role pattern — defaults declare `composition_name`, meta depends on `composition-common`, tasks template the compose file and env file then start the stack via `community.docker.docker_compose_v2`. Traefik handles TLS termination and routing for `chat.<domain>`.

**Tech Stack:** Ansible, Docker Compose v2, Traefik, Open WebUI (`ghcr.io/open-webui/open-webui:main`)

---

## File Map

| Action | Path |
|--------|------|
| Create | `ansible/roles/composition-open-webui/defaults/main.yaml` |
| Create | `ansible/roles/composition-open-webui/meta/main.yaml` |
| Create | `ansible/roles/composition-open-webui/tasks/main.yaml` |
| Create | `ansible/roles/composition-open-webui/templates/docker-compose.yaml.j2` |
| Create | `ansible/roles/composition-open-webui/templates/environment_vars.j2` |
| Modify | `ansible/inventory/host_vars/host-storage/core.yaml` |
| Modify | `ansible/playbooks/baremetal/host-storage/compositions.yaml` |

---

### Task 1: Create role defaults and meta

**Files:**
- Create: `ansible/roles/composition-open-webui/defaults/main.yaml`
- Create: `ansible/roles/composition-open-webui/meta/main.yaml`

- [ ] **Step 1: Create defaults**

Create `ansible/roles/composition-open-webui/defaults/main.yaml`:

```yaml
# Composition name (used by composition-common dependency)
composition_name: open-webui

# Ollama API URL. Defaults to Malcolm (Mac Mini M4) LAN IP.
# Override per-host if Ollama is running elsewhere.
composition_open_webui_ollama_base_url: "http://192.168.1.150:11434"
```

- [ ] **Step 2: Create meta**

Create `ansible/roles/composition-open-webui/meta/main.yaml`:

```yaml
dependencies:
  - role: composition-common
    vars:
      composition_name: open-webui
```

- [ ] **Step 3: Commit**

```bash
git add ansible/roles/composition-open-webui/defaults/main.yaml \
        ansible/roles/composition-open-webui/meta/main.yaml
git commit -m "feat(composition-open-webui): add role defaults and meta"
```

---

### Task 2: Create Docker Compose and env templates

**Files:**
- Create: `ansible/roles/composition-open-webui/templates/docker-compose.yaml.j2`
- Create: `ansible/roles/composition-open-webui/templates/environment_vars.j2`

- [ ] **Step 1: Create docker-compose template**

Create `ansible/roles/composition-open-webui/templates/docker-compose.yaml.j2`:

```yaml
# code: language=ansible
name: "{{ composition_name }}"
services:
  open-webui:
    container_name: open-webui
    image: ghcr.io/open-webui/open-webui:main
    restart: unless-stopped
    env_file: .environment_vars
    ports:
      - "3000:8080"
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.open-webui.rule=Host(`chat.{{ domain_name }}`)"
      - "traefik.http.routers.open-webui.tls=true"
      - "traefik.http.routers.open-webui.tls.certresolver=letsencrypt"
      - "traefik.http.services.open-webui.loadbalancer.server.port=8080"
    volumes:
      - "{{ composition_config }}/data:/app/backend/data"
    networks:
      - "{{ default_docker_network }}"
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

networks:
  "{{ default_docker_network }}":
    external: true
```

- [ ] **Step 2: Create env vars template**

Create `ansible/roles/composition-open-webui/templates/environment_vars.j2`:

```
TZ="Europe/Berlin"
OLLAMA_BASE_URL="{{ composition_open_webui_ollama_base_url }}"
WEBUI_AUTH=False
```

- [ ] **Step 3: Commit**

```bash
git add ansible/roles/composition-open-webui/templates/
git commit -m "feat(composition-open-webui): add docker-compose and env templates"
```

---

### Task 3: Create role tasks

**Files:**
- Create: `ansible/roles/composition-open-webui/tasks/main.yaml`

- [ ] **Step 1: Create tasks**

Create `ansible/roles/composition-open-webui/tasks/main.yaml`:

```yaml
# code: language=ansible

# ----------------------------
# Core tasks
# ----------------------------

- name: Create compose file
  ansible.builtin.template:
    src: docker-compose.yaml.j2
    dest: "{{ composition_root }}/docker-compose.yaml"
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0774"

- name: Create .env file
  ansible.builtin.template:
    src: environment_vars.j2
    dest: "{{ composition_root }}/.environment_vars"
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0774"

# ----------------------------
# Specific tasks
# ----------------------------

- name: Create data directory
  ansible.builtin.file:
    path: "{{ composition_config }}/data"
    state: directory

- name: Run Configure DNS role
  ansible.builtin.include_role:
    name: "network-register-subdomain"
  vars:
    configure_dns_subdomains:
      - chat

# ----------------------------
# Start composition
# ----------------------------

- name: Start Docker Compose project
  community.docker.docker_compose_v2:
    project_src: "{{ composition_root }}"
    state: present
    build: always
    remove_orphans: true
```

- [ ] **Step 2: Commit**

```bash
git add ansible/roles/composition-open-webui/tasks/main.yaml
git commit -m "feat(composition-open-webui): add role tasks"
```

---

### Task 4: Wire up host-storage

**Files:**
- Modify: `ansible/inventory/host_vars/host-storage/core.yaml`
- Modify: `ansible/playbooks/baremetal/host-storage/compositions.yaml`

- [ ] **Step 1: Add CNAME to host-storage host_vars**

In `ansible/inventory/host_vars/host-storage/core.yaml`, add `chat.{{ domain_name }}` to the `cnames` list. The list currently ends with `loki.{{ domain_name }}`:

```yaml
  - loki.{{ domain_name }}
  - chat.{{ domain_name }}
```

- [ ] **Step 2: Add role to compositions playbook**

In `ansible/playbooks/baremetal/host-storage/compositions.yaml`, append the role at the end of the roles list (after `composition-libretranslate`):

```yaml
    - role: composition-libretranslate
    - role: composition-open-webui
```

- [ ] **Step 3: Commit**

```bash
git add ansible/inventory/host_vars/host-storage/core.yaml \
        ansible/playbooks/baremetal/host-storage/compositions.yaml
git commit -m "feat(host-storage): add open-webui composition"
```

---

### Task 5: Deploy and verify

- [ ] **Step 1: Run the compositions playbook**

```bash
ansible-playbook ansible/playbooks/baremetal/host-storage/compositions.yaml
```

Expected: `ok` or `changed` for open-webui tasks, no failures. All other roles are idempotent and will report `ok`.

- [ ] **Step 2: Verify container is running on host-storage**

```bash
ansible host-storage -m command -a "docker ps --filter name=open-webui --format '{{.Status}}'"
```

Expected output: `Up X minutes (healthy)` or similar.

- [ ] **Step 3: Verify Open WebUI is reachable**

From any machine on Tailscale or LAN, open `https://chat.<domain>` in a browser.

Expected: Open WebUI loads with no login prompt (auth disabled). The Ollama models dropdown should show `gemma3:4b` pulled from Malcolm.

- [ ] **Step 4: Push to origin**

```bash
git push origin main
```
