# kagimcp Composition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the Kagi MCP server as a Docker Compose composition on server-64gb-storage, accessible at `kagimcp.<domain>/mcp` via Traefik with TLS.

**Architecture:** A new `composition-mcp-kagisearch` Ansible role bundles a `Dockerfile.j2` template (installs `kagimcp` from PyPI), a Docker Compose file with Traefik labels, and an env file containing the Kagi API key from Ansible Vault. The role follows the standard `composition-*` pattern: depends on `composition-common`, templates files to `{{ composition_root }}`, registers a DNS subdomain, then starts the container.

**Tech Stack:** Ansible, Docker Compose v2, Traefik (existing), Ansible Vault (beanpod identity), Python 3.12 slim image, kagimcp PyPI package

---

## File Map

| Action | Path |
|---|---|
| Create | `roles/composition-mcp-kagisearch/defaults/main.yaml` |
| Create | `roles/composition-mcp-kagisearch/meta/main.yaml` |
| Create | `roles/composition-mcp-kagisearch/tasks/main.yaml` |
| Create | `roles/composition-mcp-kagisearch/templates/Dockerfile.j2` |
| Create | `roles/composition-mcp-kagisearch/templates/docker-compose.yaml.j2` |
| Create | `roles/composition-mcp-kagisearch/templates/environment_vars.j2` |
| Create | `inventory/host_vars/server-64gb-storage/vault_mcp_kagisearch.yaml` |
| Modify | `playbooks/hosts/server-64gb-storage/core.yaml` |

---

### Task 1: Create vault entry for Kagi API key

**Files:**
- Create: `inventory/host_vars/server-64gb-storage/vault_mcp_kagisearch.yaml`

- [ ] **Step 1: Encrypt your Kagi API key**

Find your Kagi API key at https://kagi.com/settings?p=api (you must have an existing key — do not generate a new one here). Then encrypt it:

```bash
ansible-vault encrypt_string "YOUR_KAGI_API_KEY_HERE" --name 'vault_mcp_kagisearch_kagi_api_key'
```

The output will look like:

```
vault_mcp_kagisearch_kagi_api_key: !vault |
          $ANSIBLE_VAULT;1.2;AES256;beanpod
          61333035...
          ...
```

- [ ] **Step 2: Create the vault file**

Create `inventory/host_vars/server-64gb-storage/vault_mcp_kagisearch.yaml` and paste the output from step 1 as the entire file content. Example structure (your encrypted value will differ):

```yaml
vault_mcp_kagisearch_kagi_api_key: !vault |
          $ANSIBLE_VAULT;1.2;AES256;beanpod
          61333035396466386632316362363232356530313165656464663438323035303635306165633631
          3665323561316536306632326466316432303733663836350a376635616461316161616663346363
          65363230333832623163323766666565343030613735393230666162386161626432396432656434
          6361633136383732620a303963663566613332643665333534653062303939663536346461383133
          34376138633336666565613434306538613964613533323338343961643364333363346162616363
          38656263333738336535653431663662653037303562393465656365313335336637656130376238
          39663431373561366532306530346336383661666134623938623665303066643937373264333136
          39343062653535653366
```

- [ ] **Step 3: Verify the vault file decrypts correctly**

```bash
ansible -i inventory/hosts.yaml server-64gb-storage -m debug \
  -a "var=vault_mcp_kagisearch_kagi_api_key"
```

Expected: output showing the plaintext API key value under `vault_mcp_kagisearch_kagi_api_key`.

- [ ] **Step 4: Commit**

```bash
git add inventory/host_vars/server-64gb-storage/vault_mcp_kagisearch.yaml
git commit -m "feat(composition-mcp-kagisearch): add vault entry for Kagi API key"
```

---

### Task 2: Create role defaults and meta

**Files:**
- Create: `roles/composition-mcp-kagisearch/defaults/main.yaml`
- Create: `roles/composition-mcp-kagisearch/meta/main.yaml`

- [ ] **Step 1: Create the directory structure**

```bash
mkdir -p roles/composition-mcp-kagisearch/{defaults,meta,tasks,templates}
```

- [ ] **Step 2: Create defaults/main.yaml**

```yaml
# code: language=ansible
composition_name: kagimcp

composition_mcp_kagisearch_version: "1.0.0"

composition_mcp_kagisearch_subdomains:
  - kagimcp
```

- [ ] **Step 3: Create meta/main.yaml**

```yaml
dependencies:
  - role: composition-common
    vars:
      composition_name: kagimcp
```

- [ ] **Step 4: Commit**

```bash
git add roles/composition-mcp-kagisearch/defaults/main.yaml \
        roles/composition-mcp-kagisearch/meta/main.yaml
git commit -m "feat(composition-mcp-kagisearch): add role defaults and meta"
```

---

### Task 3: Create Dockerfile template

**Files:**
- Create: `roles/composition-mcp-kagisearch/templates/Dockerfile.j2`

- [ ] **Step 1: Create templates/Dockerfile.j2**

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN pip install kagimcp=={{ composition_mcp_kagisearch_version }}

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "kagimcp --http --host 0.0.0.0 --port ${PORT}"]
```

Note: `{{ composition_mcp_kagisearch_version }}` is an Ansible variable substituted at template time — the resulting `Dockerfile` on the server contains the literal version string.

- [ ] **Step 2: Commit**

```bash
git add roles/composition-mcp-kagisearch/templates/Dockerfile.j2
git commit -m "feat(composition-mcp-kagisearch): add Dockerfile template"
```

---

### Task 4: Create Docker Compose template

**Files:**
- Create: `roles/composition-mcp-kagisearch/templates/docker-compose.yaml.j2`

- [ ] **Step 1: Create templates/docker-compose.yaml.j2**

```yaml
# code: language=ansible
name: "{{ composition_name }}"
services:
  kagimcp:
    container_name: kagimcp
    build:
      context: .
      dockerfile: Dockerfile
    restart: unless-stopped
    env_file: .environment_vars
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.kagimcp.rule=Host(`kagimcp.{{ domainname_infra }}`)"
      - "traefik.http.routers.kagimcp.tls=true"
      - "traefik.http.routers.kagimcp.tls.certresolver=letsencrypt"
      - "traefik.http.services.kagimcp.loadbalancer.server.port=8000"
    networks:
      - "{{ default_docker_network }}"

networks:
  "{{ default_docker_network }}":
    external: true
```

- [ ] **Step 2: Commit**

```bash
git add roles/composition-mcp-kagisearch/templates/docker-compose.yaml.j2
git commit -m "feat(composition-mcp-kagisearch): add Docker Compose template"
```

---

### Task 5: Create environment vars template

**Files:**
- Create: `roles/composition-mcp-kagisearch/templates/environment_vars.j2`

- [ ] **Step 1: Create templates/environment_vars.j2**

```
KAGI_API_KEY="{{ vault_mcp_kagisearch_kagi_api_key }}"
```

- [ ] **Step 2: Commit**

```bash
git add roles/composition-mcp-kagisearch/templates/environment_vars.j2
git commit -m "feat(composition-mcp-kagisearch): add environment vars template"
```

---

### Task 6: Create role tasks

**Files:**
- Create: `roles/composition-mcp-kagisearch/tasks/main.yaml`

- [ ] **Step 1: Create tasks/main.yaml**

```yaml
# code: language=ansible

- name: "Create Dockerfile"
  ansible.builtin.template:
    src: Dockerfile.j2
    dest: "{{ composition_root }}/Dockerfile"
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0644"

- name: "Create compose file"
  ansible.builtin.template:
    src: docker-compose.yaml.j2
    dest: "{{ composition_root }}/docker-compose.yaml"
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0644"

- name: "Create .env file"
  ansible.builtin.template:
    src: environment_vars.j2
    dest: "{{ composition_root }}/.environment_vars"
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0644"

- name: Register DNS subdomain
  ansible.builtin.include_role:
    name: "network-register-subdomain"
  vars:
    configure_dns_subdomains: "{{ composition_mcp_kagisearch_subdomains }}"

- name: Start Docker Compose project
  community.docker.docker_compose_v2:
    project_src: "{{ composition_root }}"
    state: present
    build: always
    remove_orphans: true
  notify: Restart Traefik
```

- [ ] **Step 2: Commit**

```bash
git add roles/composition-mcp-kagisearch/tasks/main.yaml
git commit -m "feat(composition-mcp-kagisearch): add role tasks"
```

---

### Task 7: Add role to storage host playbook

**Files:**
- Modify: `playbooks/hosts/server-64gb-storage/core.yaml` (after line 81, after `composition-paperless-ngx`)

- [ ] **Step 1: Add the role entry**

In `playbooks/hosts/server-64gb-storage/core.yaml`, add after the `composition-paperless-ngx` block (currently around line 80-81):

```yaml
    - role: composition-mcp-kagisearch
      tags: [compositions]
```

The surrounding context should look like:

```yaml
    - role: composition-paperless-ngx
      tags: [compositions, composition-paperless-ngx]
    - role: composition-mcp-kagisearch
      tags: [compositions]
    - role: system-emailbackup
```

- [ ] **Step 2: Commit**

```bash
git add playbooks/hosts/server-64gb-storage/core.yaml
git commit -m "feat(composition-mcp-kagisearch): add to storage host playbook"
```

---

### Task 8: Deploy and verify

- [ ] **Step 1: Dry-run the role only**

```bash
ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml \
  --tags compositions \
  --limit server-64gb-storage \
  --check
```

Expected: tasks show as `changed` (would create files, start container) with no errors. If Ansible reports a vault decryption error, the vault file from Task 1 is malformed — re-check it.

- [ ] **Step 2: Deploy**

```bash
ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml \
  --tags compositions \
  --limit server-64gb-storage
```

Expected: all tasks complete without errors. The Docker image build will take ~30 seconds on first run.

- [ ] **Step 3: Verify the container is running**

```bash
ssh storage "docker ps --filter name=kagimcp --format '{{.Names}}\t{{.Status}}'"
```

Expected: `kagimcp    Up X seconds`

- [ ] **Step 4: Smoke-test the MCP endpoint**

```bash
ssh storage "curl -sf http://localhost:8000/mcp \
  -X POST \
  -H 'content-type: application/json' \
  -H 'accept: application/json, text/event-stream' \
  -d '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\"}'"
```

Expected: a JSON response listing `kagi_search_fetch` and `kagi_extract` tools.

- [ ] **Step 5: Verify HTTPS via Traefik**

From your local machine (requires Tailscale):

```bash
curl -sf "https://kagimcp.$(ansible -i inventory/hosts.yaml all -m debug \
  -a 'var=domainname_infra' --limit server-64gb-storage 2>/dev/null \
  | grep domainname_infra | awk -F'"' '{print $4}')/mcp" \
  -X POST \
  -H 'content-type: application/json' \
  -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

Expected: same JSON tools list response over HTTPS.

- [ ] **Step 6: Configure a client**

To use from Claude Desktop, add to your MCP config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "kagi": {
      "url": "https://kagimcp.<your-domain>/mcp"
    }
  }
}
```

Replace `<your-domain>` with your actual domain (the value of `domainname_infra`).
