# Reverse Proxy

Deploys [Traefik v3](https://traefik.io/) as the central HTTP/HTTPS reverse proxy for all Docker Compose services. Traefik auto-discovers containers through Docker socket labels, terminates TLS with a Let's Encrypt DNS challenge (Hetzner DNS provider), and redirects all HTTP traffic to HTTPS. Traefik exposes the dashboard at `traefik.<hostname>.<domain>`.

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

You can deploy static provider files in `templates/providers/` to `<composition_config>/providers/` through `traefik_providers`. Pre-built providers exist for: `esphome`, `gotosocial`, `homeassistant`, `immich`, `musicassistant`, `personalsite`, `watchyourlan`.

`reverseproxy_vm_routes` supports dynamic VM route proxying. Each entry specifies a `name`, `host`, `backend`, and optional `middlewares` list.

## Integrations

- **DNS**: Registers `whoami.<hostname>` and `traefik.<hostname>` subdomains via `network-register-subdomain`
- **Let's Encrypt**: DNS challenge via Hetzner nameservers. Cert email from `domainname_personal`
- **Docker**: All other compositions route through this proxy via `traefik.enable=true` labels on the shared `default_docker_network`
