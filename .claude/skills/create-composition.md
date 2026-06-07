---
name: create-composition
description: Use when creating a new Docker Compose-based Ansible role (composition-*) in this repo, given a GitHub repo or installation docs link.
---

# Create a Composition Role

## Overview

Compositions are Ansible roles (`roles/composition-<name>/`) that deploy a Docker Compose app. The `composition-common` dependency handles ZFS datasets, directory creation, and the Docker network — the role only needs its own templates and app-specific tasks.

## Step 1 — Read the source docs

Fetch the project's GitHub page or install docs. Look for:

- The official `docker-compose.yml` — use as the starting template
- Required environment variables
- Port the app listens on (needed for Traefik `loadbalancer.server.port`)
- Any data dirs that must exist before first run
- Secrets or passwords that need generating

## Step 2 — Directory structure

```
roles/composition-<name>/
  defaults/main.yaml
  meta/main.yaml
  tasks/main.yaml
  templates/docker-compose.yaml.j2
  templates/environment_vars.j2
  README.md
```

Use `templates/.env` instead of `environment_vars.j2` only if the app hard-requires a file named `.env` (e.g. immich).

## Step 3 — File contents

### `defaults/main.yaml`

```yaml
# Composition name (used by composition-common dependency)
composition_name: <name>
composition_<name>_subdomains:
  - <name>

# Vault-backed secrets reference the vault_ prefix:
# composition_<name>_secret_key: "{{ vault_<name>_secret_key }}"
```

### `meta/main.yaml`

```yaml
dependencies:
  - role: composition-common
    vars:
      composition_name: <name>
```

### `tasks/main.yaml`

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

# Uncomment if the app needs subdirectories under config/:
# - name: Create directories
#   ansible.builtin.file:
#     path: "{{ composition_config }}/{{ dir_item }}"
#     state: directory
#     mode: "0755"
#   loop_control:
#     loop_var: dir_item
#   loop:
#     - data

- name: Run Configure DNS role
  ansible.builtin.include_role:
    name: "network-register-subdomain"
  vars:
    configure_dns_subdomains: "{{ composition_<name>_subdomains }}"

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

### `templates/docker-compose.yaml.j2`

```yaml
# code: language=ansible
name: "{{ composition_name }}"
services:
  <name>:
    container_name: <name>
    image: <image>:<tag>
    restart: unless-stopped
    env_file: .environment_vars
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.<name>.rule=Host(`<name>.{{ domainname_infra }}`)"
      - "traefik.http.routers.<name>.tls=true"
      - "traefik.http.routers.<name>.tls.certresolver=letsencrypt"
      - "traefik.http.services.<name>.loadbalancer.server.port=<PORT>"
    volumes:
      - "{{ composition_config }}:/data"
    networks:
      - "{{ default_docker_network }}"

networks:
  "{{ default_docker_network }}":
    external: true
```

Key variables available in templates:
- `composition_name` — Docker Compose project name
- `composition_root` — `/{{ compositions_dataset }}/<name>` — where the compose file lives
- `composition_config` — `{{ composition_root }}/config` — mount point for app data
- `domainname_infra` — internal Tailscale domain
- `default_docker_network` — always the same, allowing apps to talk to each other.
- `ansible_user` — the target host user

If the app doesn't need Traefik (internal-only), omit `labels:` entirely. If it binds a host port, use `"127.0.0.1:<host>:<container>"` under `ports:`.

### `templates/environment_vars.j2`

```ini
TZ="Europe/Berlin"
# Add app env vars here; reference Ansible vars with {{ var_name }}
```

## Step 4 — Secrets

Store encrypted secrets in the target host's vault file:

```
inventory/host_vars/<host>/vault_<name>.yaml
```

Generate and encrypt:
```bash
ansible-vault encrypt_string "$(openssl rand -hex 32)" --name 'vault_<name>_secret_key'
```

Reference in `defaults/main.yaml`:
```yaml
<name>_secret_key: "{{ vault_<name>_secret_key }}"
```

Reference in `templates/environment_vars.j2`:
```ini
SECRET_KEY="{{ <name>_secret_key }}"
```

## Step 5 (optiona) — Wire into a host playbook

If the user has soecified a host, add to `roles:` in `playbooks/hosts/<host>/core.yaml`:

```yaml
- role: composition-<name>
  tags: [composition, composition-<name>]
```

## Common variations

**Multiple services (app + postgres/redis):** Keep all in one `docker-compose.yaml.j2`. Add a `Create directories` task for the DB data dir. Set `DB_DATA_LOCATION="{{ composition_config }}/postgres"` in the env template.

**Multiple subdomains:** Add entries to the subdomains list in defaults. Add extra Traefik router label sets for each subdomain.

**No web UI / no Traefik:** Ask the user if they would like to create a subdomain. If they decline, omit the `labels:` block and DNS task entirely.
