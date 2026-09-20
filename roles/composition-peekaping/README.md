# Peekaping

[Peekaping](https://github.com/0xfurai/peekaping) is a self-hosted uptime
monitoring tool — an Uptime Kuma alternative with an API-first design (a Go
backend, React frontend, and SQLite database, all bundled into one image).

It replaced `composition-uptime-kuma`, which was removed once this role's
monitor sync was proven.

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

## Host liveness is TCP, not ICMP

Peekaping's ping check reports success even when nothing answers. Verified
on this deployment against `192.168.1.249`, an address with no host on it:
`ping` from the same machine, and from another container on the same Docker
network, showed 100% loss with an incomplete ARP entry, while Peekaping
recorded "Ping successful, RTT: 6.3ms". Upstream:
[0xfurai/peekaping#226](https://github.com/0xfurai/peekaping/issues/226),
where another user reports the same false positives.

Neither documented workaround helps:

- `net.ipv4.ping_group_range` (set in the compose file) does remove the
  separate `ping: executable file not found in $PATH` heartbeats the image
  produces, so it is kept — but the false successes continue.
- `cap_add: NET_RAW` changes nothing, because Docker already grants it.
  Tried and reverted.

So host monitors connect to SSH (`composition_peekaping_ssh_port`) instead.
That proves more than ICMP anyway: the host is reachable for Ansible.

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
   - One **tcp** monitor per host in the `infra` group (`host_ipv4:22`).
   - One **http** monitor per cname across the `infra` group — the same
     `cnames:` / `compositions:` data that drives DNS registration via
     `infra-named` — plus each host's `cnames_additional`.
   - One **tcp** monitor per entry in any host's `tcp_monitors_additional`
     — for non-HTTP, non-composition services (e.g. `system-tts-pocket-tts`'s
     raw Wyoming protocol port) that have no cname to derive from. Each
     entry is `{name, host, port}`; see
     `inventory/host_vars/apple-macmini-m4-16gb-malcolm/core.yaml` for an
     example.
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
