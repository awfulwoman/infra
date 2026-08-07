# Server Cert Distribution

Serves `infra_certbot_distribution_dir` (the fullchain + key `infra-certbot`
publishes there, see `infra_certbot_domains[].distribute`) over plain HTTP,
bound only to the host's Tailscale address. Used by `client-cert-distribution`
on other infra hosts to pull the internal wildcard cert without each host
running its own ACME.

## What it does

Templates a systemd unit running `python3 -m http.server` bound to
`server_cert_distribution_bind_address:server_cert_distribution_port`, serving
`server_cert_distribution_source_dir` read-only. No new package - `python3` is
already required by Ansible itself.

| Variable | Default | Description |
|---|---|---|
| `server_cert_distribution_port` | `8420` | Port the HTTP server listens on. Must match `client_cert_distribution_port` on every consuming host. |
| `server_cert_distribution_bind_address` | `{{ host_tailscale_ipv4 }}` | Bind address - the server is never reachable from the LAN or WAN, only the tailnet. |
| `server_cert_distribution_source_dir` | `{{ infra_certbot_distribution_dir }}` | Directory served. |

## Access control

Plain HTTP, no authentication at the application layer - access control is
layered underneath it:

1. **Host firewall**: on hosts running `network_routing_firewall: true` (e.g.
   bertha), `network-routing-basic` already allows all INPUT from the
   `tailscale0` interface unconditionally (the existing out-of-band management
   backstop) - no new firewall rule was needed for this port.
2. **Tailscale ACL** (network-wide, not yet wired up): scopes *which* tailnet
   devices can reach this port to infra hosts specifically, rather than every
   device on the tailnet. Until that's in place, anything on the tailnet that
   can route to this host can reach the bundle.

## Design notes

- Runs as `ansible_user`, not root - the distribution directory and its
  contents are already owned by that user (see `infra-certbot`), so no
  privilege elevation is needed to read them.
- `Restart=on-failure` keeps the server up across transient failures without
  needing a health-check loop of its own.
