# Design: Extract zfs-api app into its own repository

**Date:** 2026-05-27

## Goal

Move the Python application currently embedded in `roles/composition-zfs-api/files/app/` into a standalone GitHub repository (`awfulwoman/zfs-api`). The composition role stays in this repo but switches from building the image locally to pulling a prebuilt image from GHCR.

## New repository: `awfulwoman/zfs-api`

**Contents** — everything currently under `roles/composition-zfs-api/files/app/`:
- `Dockerfile`
- `main.py`
- `requirements.txt`
- `routers/` (`__init__.py`, `pools.py`, `datasets.py`, `snapshots.py`, `backups.py`, `metrics.py`)
- `utils/` (`__init__.py`, `zfs_commands.py`, `parsers.py`)

**CI: `.github/workflows/docker.yaml`**
- Trigger: push to `main`
- Builds image and pushes `ghcr.io/awfulwoman/zfs-api:latest` to GHCR
- Repository is public; no registry auth required to pull

**No semver tagging.** `latest` only.

## Changes to `composition-zfs-api` in this repo

### Remove

- `files/app/` directory and all contents
- Tasks: `Create directories`, `Copy app files`, `Copy router modules`, `Copy utils modules`

### Keep (unchanged)

- `templates/swagger.yaml.j2` — rendered per-host, mounted into container
- `templates/environment_vars.j2`
- `defaults/main.yaml`
- DNS and start tasks

### `templates/docker-compose.yaml.j2`

Replace:
```yaml
build:
  context: "{{ composition_config }}/app"
```

With:
```yaml
image: ghcr.io/awfulwoman/zfs-api:latest
```

Add volume mount for the host-specific swagger spec:
```yaml
- {{ composition_config }}/app/swagger.yaml:/app/swagger.yaml:ro
```

### `tasks/main.yaml`

- Remove the four file-copy task blocks
- Slim the `Create directories` task to only create `app/` (for the swagger.yaml destination)
- Keep the `Create Swagger API documentation` task (still renders and deploys swagger.yaml)
- Change `docker_compose_v2`: remove `build: always`, no `pull` flag — just `state: present, remove_orphans: true`

## Deployment lifecycle

- **Initial deploy:** Ansible runs `docker compose up`; Docker pulls the image from GHCR since it's not cached
- **App updates:** Push to `awfulwoman/zfs-api` main → GitHub Actions builds → pushes `latest` to GHCR → Watchtower (via `composition-container-management`) detects the new digest and restarts the container automatically
- **Config updates:** Ansible rerenders templates and restarts compose — no image pull involved

## What does NOT change

- All role variables (`defaults/main.yaml`) — unchanged
- Environment variable contract between Ansible and the app — unchanged
- The swagger.yaml still renders per-host with `ansible_facts['hostname']` and `domainname_infra`
- Traefik integration, DNS registration, volume mounts for ZFS devices and policy paths — all unchanged
