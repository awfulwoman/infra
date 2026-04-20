# Reverse Proxy

Deploys [Traefik v3](https://traefik.io/) as the central HTTP/HTTPS reverse proxy for all Docker Compose services. Traefik auto-discovers containers via Docker socket labels, terminates TLS using Let's Encrypt DNS challenge (Hetzner DNS provider), and redirects all HTTP traffic to HTTPS. The dashboard is exposed at `traefik.<hostname>.<domain>`.

## Optional components

| Variable | Default | Description |
|---|---|---|
| `reverseproxy_use_letsencrypt` | `true` | Enable Let's Encrypt TLS via Hetzner DNS challenge |
| `reverseproxy_catchall` | `false` | Deploy an nginx catch-all for unmatched routes (returns custom page) |
| `reverseproxy_statuspage` | `false` | Deploy an nginx container serving custom HTTP error pages |
| `reverseproxy_whoami` | `false` | Deploy `traefik/whoami` debug service at `whoami.<hostname>.<domain>` |
| `reverseproxy_traefik_domain` | `traefik.<hostname>.<domain>` | Hostname for the Traefik dashboard |
| `reverseproxy_vm_routes` | unset | List of static proxy routes to services on QEMU VMs (internal NAT) |

## Ports

| Port | Protocol | Purpose |
|---|---|---|
| 80 | TCP | HTTP (redirects to HTTPS) |
| 443 | TCP | HTTPS |

## Providers

Static provider files in `templates/providers/` can be deployed to `<composition_config>/providers/` via `traefik_providers`. Pre-built providers exist for: `esphome`, `gotosocial`, `homeassistant`, `immich`, `musicassistant`, `personalsite`, `watchyourlan`.

Dynamic VM route proxying is supported via `reverseproxy_vm_routes` — each entry specifies a `name`, `host`, `backend`, and optional `middlewares` list.

## Integrations

- **DNS**: Registers `whoami.<hostname>` and `traefik.<hostname>` subdomains via `network-register-subdomain`
- **Let's Encrypt**: DNS challenge via Hetzner nameservers; cert email from `vault_personal_domain`
- **Docker**: All other compositions route through this proxy via `traefik.enable=true` labels on the shared `default_docker_network`
