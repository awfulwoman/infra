# network-tailscale-dns

This role sets the tailnet's global DNS nameservers to `tailscale_dns_nameservers`, in that order. It reads the current list first and writes only when the list differs. The role delegates the OAuth credential exchange to [`network-tailscale-token`](../network-tailscale-token/README.md).

The setting is tailnet-wide, so run the role on one host only (bertha). With `tailscale_dns_nameservers` empty (the default), the role does nothing.

| Variable | Default | Purpose |
|----------|---------|---------|
| `tailscale_dns_nameservers` | `[]` | Nameserver addresses, in order |
| `tailscale_api_base` | `https://api.tailscale.com/api/v2` | API root |

The OAuth client needs the `dns` scope with write access. Without it, the write fails with `403`. All API calls use `no_log`.
