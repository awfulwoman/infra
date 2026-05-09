# Network Register Subdomain

Creates DNS A records in Hetzner DNS pointing a list of subdomains at the host's Tailscale IP address.

All hosts in this infrastructure are accessed via Tailscale. This role bridges Tailscale's private mesh network with a public DNS zone managed on Hetzner, so that services can be reached by human-friendly hostnames (e.g., `gitea.example.com`) without exposing real IP addresses.

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `configure_dns_subdomains` | `[]` | List of subdomain labels to register (e.g., `["gitea", "jellyfin"]`) |
| `configure_dns_domain` | `{{ domainname_infra }}` | The DNS zone to register records in |
| `vault_hetzner_api_key_rw` | _(required)_ | Hetzner DNS API key with write access, stored in Ansible Vault |

## Design Notes

- The role reads the host's Tailscale IPv4 address from `ansible_facts['tailscale0']['ipv4']['address']` and skips silently if the interface is not present — hosts without Tailscale are unaffected.
- Uses `hetzner.hcloud.zone_rrset` which manages the full record set for a name, so existing records for the same subdomain are replaced rather than appended.
- The `domainname_infra` variable is a global group var used throughout the repo, so `configure_dns_domain` rarely needs to be overridden.
- Typically applied per-composition or per-role rather than globally, since each service owns its own subdomain registration.
