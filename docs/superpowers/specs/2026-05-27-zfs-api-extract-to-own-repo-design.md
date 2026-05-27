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
- Multi-arch build for `linux/amd64` and `linux/arm64` — the fleet includes `raspberry-pi4-4gb-albion` (ARM64). Uses `docker/setup-qemu-action`, `docker/setup-buildx-action`, `docker/login-action`, and `docker/build-push-action` with `platforms: linux/amd64,linux/arm64`.
- Pushes `ghcr.io/awfulwoman/zfs-api:latest` to GHCR
- Repository is public; no registry auth required to pull

**No semver tagging.** `latest` only.

**Dockerfile contract:** The new repo's Dockerfile MUST use `WORKDIR /app` so that `main.py` resolves `Path(__file__).parent / "swagger.yaml"` to `/app/swagger.yaml`, matching the volume mount path defined in the composition role. The current Dockerfile's unusual `WORKDIR .` should be cleaned up as part of the move.

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

## Cutover ordering

The migration must happen in this order to avoid broken Ansible runs:

1. Create the `awfulwoman/zfs-api` repo with code + CI workflow
2. Push to `main` and wait for the first successful CI build — confirm `ghcr.io/awfulwoman/zfs-api:latest` exists and contains both `linux/amd64` and `linux/arm64` manifests
3. Merge the infra-repo changes (this PR)
4. Roll out per host (see below)

If step 3 happens before step 2, every host running the playbook will fail at `docker compose up` because the image doesn't exist.

## Rollout & verification

Deploy to **one host first** (recommend `server-64gb-storage` — it's the primary target and has the most ZFS state to exercise):

1. Run the host's composition playbook
2. Verify the container is running: `docker ps | grep zfs-api`
3. Verify endpoints respond:
   - `curl -s https://zfs-api.<host>.<domain>/api/v1/health`
   - `curl -s https://zfs-api.<host>.<domain>/api/v1/pools | jq`
   - `curl -s https://zfs-api.<host>.<domain>/metrics | head`
4. Verify Swagger UI shows the correct server URL: `https://zfs-api.<host>.<domain>/api/docs`

Only after the first host passes, roll out to: `minipc-8gb-homebrain`, `deedee`, `server-8gb-backups`, then `raspberry-pi4-4gb-albion` (ARM target — verify last to confirm multi-arch image works).

## Post-cutover cleanup

After successful rollout, each host will still have the old locally-built `zfs-api` image in its local Docker cache (unused but taking disk). Optional one-time cleanup per host:

```bash
docker image prune -f
```

Not blocking — Watchtower and Ansible don't care about it.

## What does NOT change

- All role variables (`defaults/main.yaml`) — unchanged
- Environment variable contract between Ansible and the app — unchanged
- The swagger.yaml still renders per-host with `ansible_facts['hostname']` and `domainname_infra`
- Traefik integration, DNS registration, volume mounts for ZFS devices and policy paths — all unchanged
