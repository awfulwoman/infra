# 1Password Connect Composition — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `composition-1password-connect` role and deploy it to `raspberry-pi4-4gb-randolph`.

**Architecture:** Two Docker containers (`op-connect-api`, `op-connect-sync`) share a named volume and a credentials file templated from Ansible Vault. Only `op-connect-api` joins the Traefik network and receives Traefik labels. `1password-credentials.json` must be bootstrapped manually before first run.

**Tech Stack:** Ansible, Docker Compose v2, 1Password Connect, Traefik

---

## File Map

| Action   | Path |
|----------|------|
| Create   | `roles/composition-1password-connect/defaults/main.yaml` |
| Create   | `roles/composition-1password-connect/meta/main.yaml` |
| Create   | `roles/composition-1password-connect/tasks/main.yaml` |
| Create   | `roles/composition-1password-connect/templates/docker-compose.yaml.j2` |
| Create   | `roles/composition-1password-connect/templates/environment_vars.j2` |
| Create   | `roles/composition-1password-connect/templates/credentials.j2` |
| Create   | `inventory/group_vars/infra/vault_onepassword_connect.yaml` |
| Modify   | `playbooks/hosts/raspberry-pi4-4gb-randolph/core.yaml` |

---

## Pre-flight: Bootstrap credentials

Before running any playbook step, generate `1password-credentials.json` on your local machine:

```bash
op connect server create randolph --vaults <your-vault-name>
```

This writes `1password-credentials.json` to the current directory. Keep it; you need it in Task 5.

---

## Task 1: Role defaults and meta

**Files:**
- Create: `roles/composition-1password-connect/defaults/main.yaml`
- Create: `roles/composition-1password-connect/meta/main.yaml`

- [ ] **Step 1: Create defaults**

```yaml
# roles/composition-1password-connect/defaults/main.yaml
composition_name: onepassword-connect

composition_onepassword_connect_subdomain: connect
```

Note: `onepassword-connect` not `1password-connect` — Docker Compose project names must start with a letter.

- [ ] **Step 2: Create meta**

```yaml
# roles/composition-1password-connect/meta/main.yaml
dependencies:
  - role: composition-common
    vars:
      composition_name: onepassword-connect
```

- [ ] **Step 3: Commit**

```bash
git add roles/composition-1password-connect/
git commit -m "feat: add composition-1password-connect role skeleton"
```

---

## Task 2: Docker Compose template

**Files:**
- Create: `roles/composition-1password-connect/templates/docker-compose.yaml.j2`

- [ ] **Step 1: Create template**

```yaml
# roles/composition-1password-connect/templates/docker-compose.yaml.j2
# code: language=ansible
name: "{{ composition_name }}"
services:
  op-connect-api:
    image: 1password/connect-api:latest
    restart: unless-stopped
    volumes:
      - "{{ composition_config }}/1password-credentials.json:/home/opuser/.op/1password-credentials.json:ro"
      - "op-connect-data:/home/opuser/.op/data"
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.op-connect.rule=Host(`{{ composition_onepassword_connect_subdomain }}.{{ domainname_infra }}`)"
      - "traefik.http.routers.op-connect.tls=true"
      - "traefik.http.routers.op-connect.tls.certresolver=letsencrypt"
      - "traefik.http.services.op-connect.loadbalancer.server.port=8080"
    networks:
      - "{{ default_docker_network }}"

  op-connect-sync:
    image: 1password/connect-sync:latest
    restart: unless-stopped
    volumes:
      - "{{ composition_config }}/1password-credentials.json:/home/opuser/.op/1password-credentials.json:ro"
      - "op-connect-data:/home/opuser/.op/data"

volumes:
  op-connect-data:

networks:
  "{{ default_docker_network }}":
    external: true
```

- [ ] **Step 2: Commit**

```bash
git add roles/composition-1password-connect/templates/docker-compose.yaml.j2
git commit -m "feat: add docker-compose template for 1password-connect"
```

---

## Task 3: Credentials and env templates

**Files:**
- Create: `roles/composition-1password-connect/templates/credentials.j2`
- Create: `roles/composition-1password-connect/templates/environment_vars.j2`

- [ ] **Step 1: Create credentials template**

```
{{ vault_onepassword_connect_credentials }}
```

Save to `roles/composition-1password-connect/templates/credentials.j2`. This outputs the raw JSON content of `1password-credentials.json` from the vault var.

- [ ] **Step 2: Create env template**

```
TZ="Europe/Berlin"
```

Save to `roles/composition-1password-connect/templates/environment_vars.j2`. Connect containers don't use env vars for configuration; this file satisfies the composition-common convention.

- [ ] **Step 3: Commit**

```bash
git add roles/composition-1password-connect/templates/
git commit -m "feat: add credentials and env templates for 1password-connect"
```

---

## Task 4: Tasks file

**Files:**
- Create: `roles/composition-1password-connect/tasks/main.yaml`

- [ ] **Step 1: Create tasks**

```yaml
# roles/composition-1password-connect/tasks/main.yaml
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
    mode: "0644"

- name: "Create .env file"
  ansible.builtin.template:
    src: environment_vars.j2
    dest: "{{ composition_root }}/.environment_vars"
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0644"

# ----------------------------
# Specific tasks
# ----------------------------

- name: "Deploy 1password-credentials.json"
  ansible.builtin.template:
    src: credentials.j2
    dest: "{{ composition_config }}/1password-credentials.json"
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0600"

- name: Run Configure DNS role
  ansible.builtin.include_role:
    name: "network-register-subdomain"
  vars:
    configure_dns_subdomains:
      - "{{ composition_onepassword_connect_subdomain }}"

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
```

- [ ] **Step 2: Commit**

```bash
git add roles/composition-1password-connect/tasks/main.yaml
git commit -m "feat: add tasks for 1password-connect composition"
```

---

## Task 5: Vault placeholder file

**Files:**
- Create: `inventory/group_vars/infra/vault_onepassword_connect.yaml`

- [ ] **Step 1: Encrypt credentials**

Run on your local machine (requires `1password-credentials.json` from pre-flight):

```bash
ansible-vault encrypt_string "$(cat 1password-credentials.json)" \
  --name 'vault_onepassword_connect_credentials'
```

- [ ] **Step 2: Create vault file**

Paste the output from step 1 into a new file:

```yaml
# inventory/group_vars/infra/vault_onepassword_connect.yaml
vault_onepassword_connect_credentials: !vault |
  <paste ansible-vault output here>
```

- [ ] **Step 3: Verify the vault file decrypts**

```bash
ansible -i inventory/hosts.yaml raspberry-pi4-4gb-randolph \
  -m debug -a "var=vault_onepassword_connect_credentials"
```

Expected: the JSON string is printed (not an error).

- [ ] **Step 4: Commit**

```bash
git add inventory/group_vars/infra/vault_onepassword_connect.yaml
git commit -m "feat: add vault credentials for 1password-connect"
```

---

## Task 6: Update randolph core.yaml

**Files:**
- Modify: `playbooks/hosts/raspberry-pi4-4gb-randolph/core.yaml`

- [ ] **Step 1: Add system-docker and composition role**

Append to the `roles:` list in `core.yaml`:

```yaml
    - role: system-docker
      tags: [system, docker]
    - role: composition-1password-connect
      tags: [compositions, connect]
```

Full file after edit:

```yaml
- name: RANDOLPH!
  hosts: raspberry-pi4-4gb-randolph
  roles:
    - role: monitoring-healthchecksio
      monitoring_healthchecksio_ping_type: start
      tags: [monitoring]
    - role: hardware-raspberry-pi
      tags: [hardware]
    - role: bootstrap-ubuntu-server
      tags: [bootstrap]
    - role: network-netplan
      tags: [network]
    - role: infothrill.nullmailer
      become: true
    - role: system-sshkey
      tags: [system]
    - role: system-zfs
      tags: [system, zfs, system-zfs]
    - role: system-zfs-policy
      tags: [system, zfs, system-zfs-policy]
    - role: system-docker
      tags: [system, docker]
    - role: composition-1password-connect
      tags: [compositions, connect]
```

- [ ] **Step 2: Commit**

```bash
git add playbooks/hosts/raspberry-pi4-4gb-randolph/core.yaml
git commit -m "feat: add docker and 1password-connect to randolph"
```

---

## Task 7: Deploy

- [ ] **Step 1: Dry run**

```bash
ansible-playbook playbooks/hosts/raspberry-pi4-4gb-randolph/core.yaml \
  --tags compositions,connect --check
```

Expected: tasks show `changed` or `ok` with no failures. The `docker_compose_v2` task will likely show `skipped` in check mode — that's normal.

- [ ] **Step 2: Run for real**

```bash
ansible-playbook playbooks/hosts/raspberry-pi4-4gb-randolph/core.yaml \
  --tags compositions,connect
```

Expected: all tasks pass, containers start.

- [ ] **Step 3: Verify containers are running**

```bash
ansible raspberry-pi4-4gb-randolph -i inventory/hosts.yaml \
  -m command -a "docker ps --filter name=op-connect"
```

Expected: two containers — `op-connect-api` and `op-connect-sync` — both `Up`.

- [ ] **Step 4: Verify API responds**

```bash
ansible raspberry-pi4-4gb-randolph -i inventory/hosts.yaml \
  -m uri -a "url=http://localhost:8080/v1/vaults headers={'Authorization': 'Bearer $OP_CONNECT_TOKEN'}"
```

Or SSH to randolph and run:

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer <your-token>" \
  http://localhost:8080/v1/vaults
```

Expected: HTTP 200.
