# Plan: Self-host Pixelfed (GH #167)

## Context

Deploy Pixelfed (federated photo sharing) as a new `composition-pixelfed` Ansible role on `vm-awfulwoman-hetzner`. Public-facing at `pixelfed.{{ vault_personal_domain }}` for ActivityPub federation. Uses internal MySQL, Redis, and the official Pixelfed Docker image pinned to `v0.12.6`.

## Files to Create

### 1. `ansible/roles/composition-pixelfed/defaults/main.yaml`
```yaml
composition_name: pixelfed
```

### 2. `ansible/roles/composition-pixelfed/meta/main.yaml`
```yaml
dependencies:
  - role: composition-common
    vars:
      composition_name: pixelfed
```

### 3. `ansible/roles/composition-pixelfed/tasks/main.yaml`
Standard 3-section pattern (modeled on `composition-karakeep`):
- Template compose file → `{{ composition_root }}/docker-compose.yaml`
- Template env file → `{{ composition_root }}/.environment_vars`
- Create directories: `storage`, `bootstrap-cache`, `mysql-data`, `redis-data`
- Register DNS via `network-register-subdomain` (Tailscale access)
- Start via `community.docker.docker_compose_v2`

### 4. `ansible/roles/composition-pixelfed/templates/docker-compose.yaml.j2`
5 services adapted from [official compose](https://github.com/pixelfed/pixelfed/blob/dev/docker-compose.yml):

| Service | Image | Purpose |
|---------|-------|---------|
| db | `mysql:9` | Internal MySQL |
| redis | `redis:7-alpine` | Cache/queue backend |
| pixelfed | `ghcr.io/pixelfed/pixelfed:v0.12.6` | Web/API (port 8080) |
| horizon | same image | Queue worker (`php artisan horizon`) |
| scheduler | same image | Cron (`php artisan schedule:work`) |

Key decisions:
- All on `{{ default_docker_network }}` (external) - no internal network per repo convention
- Traefik labels on `pixelfed` service: `Host(`pixelfed.{{ vault_personal_domain }}`)` with letsencrypt certresolver
- `AUTORUN_LARAVEL_MIGRATION: "true"` on app container only (handles initial schema + upgrades)
- `depends_on` with `condition: service_healthy` for db/redis
- Volumes under `{{ composition_config }}/`
- Healthchecks from official compose retained

### 5. `ansible/roles/composition-pixelfed/templates/environment_vars.j2`
Key env vars:
- `APP_URL=https://pixelfed.{{ vault_personal_domain }}`
- `APP_DOMAIN=pixelfed.{{ vault_personal_domain }}`
- `APP_KEY={{ vault_pixelfed_app_key }}`
- DB connection to `pixelfed-db` container
- Redis connection to `pixelfed-redis` container
- `ACTIVITY_PUB=true`, `AP_REMOTE_FOLLOW=true`
- `TRUST_PROXIES=*` (behind Traefik)
- `LOG_CHANNEL=stderr`

## Files to Modify

### 6. `ansible/inventory/group_vars/infra/vault_compositions.yaml`
Add 3 encrypted vault variables:
- `vault_pixelfed_app_key` - Laravel APP_KEY (`base64:<44-char>`)
- `vault_pixelfed_db_password`
- `vault_pixelfed_db_root_password`

Generate via:
```bash
echo "base64:$(openssl rand -base64 32)"    # APP_KEY
openssl rand -base64 24                      # DB passwords
ansible-vault encrypt_string '<value>' --name 'vault_pixelfed_app_key'
```

### 7. `ansible/roles/infra-public-resources/defaults/main/hetzner.yaml`
Add CNAME record under `vault_personal_domain` zone (alongside existing `gts`, `shared` CNAMEs):
```yaml
- type: CNAME
  hostname: pixelfed
  value: "{{ vault_personal_domain }}"
  id: aw_a_pixelfed
```

### 8. `ansible/playbooks/virtual/vm-awfulwoman-hetzner/core.yaml`
Add `- role: composition-pixelfed` after `composition-zfs-api`

### 9. `ansible/playbooks/virtual/vm-awfulwoman-hetzner/compositions.yaml`
Add `- role: composition-pixelfed` after `composition-zfs-api`

## Verification

1. Run Terraform to provision DNS: `ansible-playbook ansible/playbooks/utility/deploy-public-resources.yaml` (or however infra-public-resources is applied)
2. Verify DNS resolves: `dig pixelfed.<personal_domain>`
3. Deploy composition: `ansible-playbook ansible/playbooks/virtual/vm-awfulwoman-hetzner/compositions.yaml`
4. Check container logs: `ssh vm-awfulwoman-hetzner "docker logs pixelfed-app"`
5. Verify migrations ran: `ssh vm-awfulwoman-hetzner "docker exec pixelfed-app php artisan migrate:status"`
6. Access web UI: `https://pixelfed.<personal_domain>`
7. Test federation: search for a known remote account

## Unresolved Questions

- Storage ownership: Pixelfed runs as www-data (uid 33). Should dirs be chowned to 33:33 or let the container entrypoint handle it?
- Does `infra-public-resources` need a separate Terraform apply step before the composition runs, or is it part of the same playbook cascade?
