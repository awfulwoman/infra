# Peekaping

[Peekaping](https://github.com/0xfurai/peekaping) is a self-hosted uptime
monitoring tool — an Uptime Kuma alternative with an API-first design (a Go
backend, React frontend, and SQLite database, all bundled into one image).

This runs alongside [`composition-uptime-kuma`](../composition-uptime-kuma/README.md)
on the same host for now, not as a replacement.

## Ports

| Port | Service |
|------|---------|
| `127.0.0.1:8383` | Web UI + REST API (also fronted by Traefik) |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/data` | SQLite database |
| `{{ composition_config }}/logs` | supervisord logs (redis, api, worker, caddy, …) |
| `{{ composition_config }}/api_key` | The Ansible-generated API key (0600) — see below |

## Monitor sync

Unlike Uptime Kuma (Socket.io only, needing a custom `uptime-kuma-api`
sidecar), Peekaping ships a native REST API with API-key auth, so Ansible
drives it directly — no sidecar needed. On every deploy, `tasks/main.yaml`:

1. Bootstraps a single admin account (`/auth/register` — Peekaping accepts
   this exactly once) and an API key, persisting the key to
   `{{ composition_config }}/api_key` since it's only ever returned at
   creation time.
2. Ensures an `ansible-managed` tag exists.
3. Builds the desired monitor list from inventory:
   - One **ping** monitor per host in the `infra` group (`host_ipv4`).
   - One **http** monitor per cname across the `infra` group — the same
     `cnames:` / `compositions:` data that drives DNS registration via
     `infra-named` — plus each host's `cnames_additional`.
4. Reconciles: creates monitors missing from Peekaping, deletes any tagged
   `ansible-managed` that are no longer desired. Monitors without the tag
   (created by hand in the UI) are never touched.

This mirrors the design in
`docs/superpowers/specs/2026-06-12-uptime-kuma-monitor-sync-design.md`,
adapted to Peekaping's REST API instead of a sync sidecar.

## Secrets

| Vault variable | Purpose |
|---|---|
| `vault_composition_peekaping_admin_email` | One-time admin registration email |
| `vault_composition_peekaping_admin_password` | One-time admin registration password |

## DNS

Registers subdomain: `peekaping`
