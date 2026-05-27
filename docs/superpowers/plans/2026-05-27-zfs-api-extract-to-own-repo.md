# zfs-api Extract to Own Repository Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the Python app from `roles/composition-zfs-api/files/app/` into a new public GitHub repo (`awfulwoman/zfs-api`), build a multi-arch image via GitHub Actions, and retask the composition role to pull that image instead of building locally.

**Architecture:** The app lives in its own repo with a GitHub Actions workflow that builds and pushes `ghcr.io/awfulwoman/zfs-api:latest` for `linux/amd64` and `linux/arm64` on every push to main. The infra repo's composition role drops all source-copy tasks and instead references the prebuilt image; a host-specific `swagger.yaml` is still rendered by Ansible and bind-mounted into the container. Watchtower handles ongoing updates.

**Tech Stack:** Python/FastAPI (existing), Docker multi-arch buildx, GitHub Actions, GHCR, Ansible `community.docker.docker_compose_v2`

---

## File Map

**New repo `awfulwoman/zfs-api`** (all created):
- `Dockerfile` — fixed `WORKDIR /app`, otherwise unchanged
- `main.py`, `requirements.txt` — copied verbatim from infra repo
- `routers/__init__.py`, `routers/pools.py`, `routers/datasets.py`, `routers/snapshots.py`, `routers/backups.py`, `routers/metrics.py` — copied verbatim
- `utils/__init__.py`, `utils/zfs_commands.py`, `utils/parsers.py` — copied verbatim
- `.github/workflows/docker.yaml` — new, multi-arch build + GHCR push

**This repo (`awfulwoman/infra`)** — modified:
- `roles/composition-zfs-api/templates/docker-compose.yaml.j2` — replace `build:` with `image:`, add swagger volume mount
- `roles/composition-zfs-api/tasks/main.yaml` — remove four file-copy task blocks, slim directory task, remove `build: always`, remove duplicate compose task
- `roles/composition-zfs-api/files/app/` — **deleted entirely**

---

### Task 1: Create `awfulwoman/zfs-api` repo and populate with app code

**Working directory:** anywhere with `gh` available (your local machine or the infra repo root)

**Files:**
- Create: new repo `awfulwoman/zfs-api` (cloned to a temp dir)

- [ ] **Step 1.1: Create the GitHub repo and clone it**

```bash
gh repo create awfulwoman/zfs-api --public --clone --description "REST API for ZFS pool, dataset, and snapshot monitoring"
cd zfs-api
```

- [ ] **Step 1.2: Copy the app source from the infra repo**

Replace `<infra-repo>` with the path to this repo:

```bash
cp <infra-repo>/roles/composition-zfs-api/files/app/main.py .
cp <infra-repo>/roles/composition-zfs-api/files/app/requirements.txt .
mkdir -p routers utils
cp <infra-repo>/roles/composition-zfs-api/files/app/routers/__init__.py routers/
cp <infra-repo>/roles/composition-zfs-api/files/app/routers/pools.py routers/
cp <infra-repo>/roles/composition-zfs-api/files/app/routers/datasets.py routers/
cp <infra-repo>/roles/composition-zfs-api/files/app/routers/snapshots.py routers/
cp <infra-repo>/roles/composition-zfs-api/files/app/routers/backups.py routers/
cp <infra-repo>/roles/composition-zfs-api/files/app/routers/metrics.py routers/
cp <infra-repo>/roles/composition-zfs-api/files/app/utils/__init__.py utils/
cp <infra-repo>/roles/composition-zfs-api/files/app/utils/zfs_commands.py utils/
cp <infra-repo>/roles/composition-zfs-api/files/app/utils/parsers.py utils/
```

- [ ] **Step 1.3: Verify the file tree**

```bash
find . -not -path './.git/*' | sort
```

Expected:
```
.
./main.py
./requirements.txt
./routers
./routers/__init__.py
./routers/backups.py
./routers/datasets.py
./routers/metrics.py
./routers/pools.py
./routers/snapshots.py
./utils
./utils/__init__.py
./utils/parsers.py
./utils/zfs_commands.py
```

---

### Task 2: Add Dockerfile with correct WORKDIR

**Working directory:** `awfulwoman/zfs-api` (cloned repo from Task 1)

**Files:**
- Create: `Dockerfile`

- [ ] **Step 2.1: Write the Dockerfile**

```dockerfile
FROM ubuntu:24.04

LABEL maintainer="ZFS API"
LABEL description="REST API for ZFS pool, dataset, and snapshot monitoring"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3.12 \
        python3-pip \
        zfsutils-linux \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --break-system-packages --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Key change from the infra repo version: `WORKDIR /app` (was `WORKDIR .`). This ensures `main.py` resolves `Path(__file__).parent / "swagger.yaml"` to `/app/swagger.yaml`, matching the bind-mount path in the composition.

---

### Task 3: Add GitHub Actions multi-arch build workflow

**Working directory:** `awfulwoman/zfs-api`

**Files:**
- Create: `.github/workflows/docker.yaml`

- [ ] **Step 3.1: Create the workflow directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 3.2: Write the workflow**

```yaml
name: Build and push Docker image

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ghcr.io/awfulwoman/zfs-api:latest
```

---

### Task 4: Commit, push, and verify CI build

**Working directory:** `awfulwoman/zfs-api`

- [ ] **Step 4.1: Initial commit and push**

```bash
git add .
git commit -m "feat: initial commit — FastAPI ZFS monitoring API"
git push origin main
```

- [ ] **Step 4.2: Watch the CI run**

```bash
gh run watch
```

Wait for it to report success. Expected output ends with:
```
✓ Build and push Docker image · build (ubuntu-latest)
```

If it fails, check logs:
```bash
gh run view --log-failed
```

- [ ] **Step 4.3: Verify the image exists and is multi-arch**

```bash
docker manifest inspect ghcr.io/awfulwoman/zfs-api:latest
```

Expected: a manifest list containing entries for both `linux/amd64` and `linux/arm64`. Look for two `"mediaType"` entries, each with `"architecture": "amd64"` and `"architecture": "arm64"`.

If `docker manifest inspect` isn't available locally, check via `gh`:
```bash
gh api /orgs/awfulwoman/packages/container/zfs-api/versions --jq '.[0].metadata.container.tags'
```

Expected: `["latest"]`

---

### Task 5: Update `docker-compose.yaml.j2` in the infra repo

**Working directory:** `awfulwoman/infra`

**Files:**
- Modify: `roles/composition-zfs-api/templates/docker-compose.yaml.j2`

- [ ] **Step 5.1: Replace the entire file**

```yaml
name: "{{ composition_name }}"
services:
  zfs-api:
    image: ghcr.io/awfulwoman/zfs-api:latest
    container_name: {{ composition_zfs_api_container_name }}
    restart: unless-stopped
    privileged: true
    volumes:
      - /dev/zfs:/dev/zfs:ro
      - {{ composition_zfs_api_zfs_policy_path }}:{{ composition_zfs_api_zfs_policy_path }}:ro
      - {{ composition_zfs_api_zfs_log_path }}:{{ composition_zfs_api_zfs_log_path }}:ro
      - {{ system_zfs_policy_cache_file }}:{{ system_zfs_policy_cache_file }}:ro
      - {{ composition_config }}/app/swagger.yaml:/app/swagger.yaml:ro
    env_file: .environment_vars
{% if composition_zfs_api_traefik_enabled %}
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.{{ composition_zfs_api_container_name }}.rule=Host(`zfs-api.{{ ansible_facts['hostname'] }}.{{ domainname_infra }}`)"
      - "traefik.http.routers.{{ composition_zfs_api_container_name }}.tls=true"
      - "traefik.http.routers.{{ composition_zfs_api_container_name }}.tls.certresolver=letsencrypt"
      - "traefik.http.services.{{ composition_zfs_api_container_name }}.loadbalancer.server.port={{ composition_zfs_api_port }}"
{% endif %}
    networks:
      - "{{ default_docker_network }}"

networks:
  "{{ default_docker_network }}":
    external: true
```

Changes from original:
- `build: context: ...` replaced with `image: ghcr.io/awfulwoman/zfs-api:latest`
- Added `{{ composition_config }}/app/swagger.yaml:/app/swagger.yaml:ro` volume mount

---

### Task 6: Update `tasks/main.yaml` in the infra repo

**Working directory:** `awfulwoman/infra`

**Files:**
- Modify: `roles/composition-zfs-api/tasks/main.yaml`

- [ ] **Step 6.1: Replace the entire file**

```yaml
# code: language=ansible

- name: Ensure composition is enabled
  ansible.builtin.assert:
    that:
      - composition_zfs_api_enabled
    fail_msg: "composition-zfs-api is not enabled"
    quiet: true

- name: Ensure ZFS is configured on host
  ansible.builtin.assert:
    that:
      - zfs is defined
    fail_msg: "ZFS must be configured (zfs variable) to use this composition"
    quiet: true

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
    mode: "0774"

# ----------------------------
# Specific tasks
# ----------------------------

- name: Create app directory
  become: true
  ansible.builtin.file:
    path: "{{ composition_config }}/app"
    state: directory
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0774"

- name: "Create Swagger API documentation"
  become: true
  ansible.builtin.template:
    src: swagger.yaml.j2
    dest: "{{ composition_config }}/app/swagger.yaml"
    owner: "{{ ansible_user }}"
    group: "{{ ansible_user }}"
    mode: "0774"

- name: Run Configure DNS role
  ansible.builtin.include_role:
    name: "network-register-subdomain"
  vars:
    configure_dns_subdomains: "{{ composition_zfs_api_subdomains }}"

# ----------------------------
# Start composition
# ----------------------------

- name: Start Docker Compose project
  community.docker.docker_compose_v2:
    project_src: "{{ composition_root }}"
    state: present
    remove_orphans: true
  notify: Restart Traefik
```

Changes from original:
- Removed: `Create directories` (loop over app, app/routers, app/utils)
- Removed: `Copy app files` task block
- Removed: `Copy router modules` task block
- Removed: `Copy utils modules` task block
- Removed: duplicate `Create compose file` task (was at the end of specific tasks)
- Replaced: `Create directories` loop → single `Create app directory` task
- Removed: `build: always` from `docker_compose_v2`

---

### Task 7: Delete `files/app/` from the infra repo

**Working directory:** `awfulwoman/infra`

**Files:**
- Delete: `roles/composition-zfs-api/files/app/` (entire directory)

- [ ] **Step 7.1: Remove the app source tree**

```bash
git rm -r roles/composition-zfs-api/files/app/
```

- [ ] **Step 7.2: Verify nothing unexpected was removed**

```bash
git status
```

Expected staged deletions:
```
deleted:    roles/composition-zfs-api/files/app/Dockerfile
deleted:    roles/composition-zfs-api/files/app/main.py
deleted:    roles/composition-zfs-api/files/app/requirements.txt
deleted:    roles/composition-zfs-api/files/app/routers/__init__.py
deleted:    roles/composition-zfs-api/files/app/routers/backups.py
deleted:    roles/composition-zfs-api/files/app/routers/datasets.py
deleted:    roles/composition-zfs-api/files/app/routers/metrics.py
deleted:    roles/composition-zfs-api/files/app/routers/pools.py
deleted:    roles/composition-zfs-api/files/app/routers/snapshots.py
deleted:    roles/composition-zfs-api/files/app/utils/__init__.py
deleted:    roles/composition-zfs-api/files/app/utils/parsers.py
deleted:    roles/composition-zfs-api/files/app/utils/zfs_commands.py
```

No other files should appear as deleted.

- [ ] **Step 7.3: Commit all infra repo changes**

```bash
git add roles/composition-zfs-api/templates/docker-compose.yaml.j2
git add roles/composition-zfs-api/tasks/main.yaml
git commit -m "feat(composition-zfs-api): switch from local build to prebuilt GHCR image

App code moved to github.com/awfulwoman/zfs-api.
Image: ghcr.io/awfulwoman/zfs-api:latest (multi-arch amd64+arm64).
Watchtower handles ongoing updates; swagger.yaml still rendered
per-host and bind-mounted at /app/swagger.yaml."
```

---

### Task 8: Deploy to first host and verify

**Working directory:** `awfulwoman/infra`

- [ ] **Step 8.1: Run the composition playbook for `server-64gb-storage`**

```bash
ansible-playbook playbooks/hosts/server-64gb-storage/compositions.yaml
```

Expected: play completes without errors. The `Start Docker Compose project` task will show `changed` on first run (pulls image, creates new container).

- [ ] **Step 8.2: Verify the container is running**

SSH to the host or use:
```bash
ansible server-64gb-storage -m command -a "docker ps --filter name=zfs-api --format '{{.Names}} {{.Status}} {{.Image}}'"
```

Expected output:
```
zfs-api   Up X seconds   ghcr.io/awfulwoman/zfs-api:latest
```

The image must show `ghcr.io/awfulwoman/zfs-api:latest`, not a locally-built hash.

- [ ] **Step 8.3: Verify API endpoints**

Replace `<host-fqdn>` with the host's actual domain (e.g. `server-64gb-storage.xberg.ber.<domain>`):

```bash
curl -sf https://zfs-api.<host-fqdn>/api/v1/health | jq
```

Expected:
```json
{"status": "healthy", "service": "zfs-api", "version": "1.0.0", "timestamp": "..."}
```

```bash
curl -sf https://zfs-api.<host-fqdn>/api/v1/pools | jq '.pools[].health'
```

Expected: one or more `"ONLINE"` values.

```bash
curl -sf https://zfs-api.<host-fqdn>/metrics | grep -c '^zfs_'
```

Expected: a non-zero number (at least 5 — confirms Prometheus metrics endpoint is alive).

- [ ] **Step 8.4: Verify swagger.yaml is loaded correctly**

```bash
curl -sf https://zfs-api.<host-fqdn>/api/openapi.json | jq '.servers[0].url'
```

Expected: `"https://zfs-api.<actual-hostname>.<domain>"` — confirms the bind-mounted swagger.yaml is being read (FastAPI's auto-generated spec has no `servers` array).

- [ ] **Step 8.5: Roll out to remaining hosts**

Repeat Step 8.1 for each remaining host in order:
1. `minipc-8gb-homebrain`
2. `deedee`
3. `server-8gb-backups`
4. `raspberry-pi4-4gb-albion` ← ARM64, verifies multi-arch image

Run the same verification checks (Steps 8.2–8.4) for the Pi specifically to confirm `linux/arm64` works.

- [ ] **Step 8.6: Optional — clean up stale local images on each host**

The old locally-built `zfs-api` images are now unreferenced. To reclaim disk:

```bash
ansible <host> -b -m command -a "docker image prune -f"
```

Or SSH and run manually. Not blocking — Watchtower ignores them.
