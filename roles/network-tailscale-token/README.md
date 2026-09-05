# network-tailscale-token

This role exchanges the Tailscale OAuth client credentials
(`tailscale_oauth_client_id` and `tailscale_oauth_client_secret`, both
mapped from vault in `inventory/group_vars/infra/core.yaml`) for a
short-lived API bearer token. It exposes the token as the
`tailscale_api_token` fact.

Every role in this repo that talks to the Tailscale API goes through this
role, instead of repeating the OAuth exchange itself:

* `network-tailscale-authkey` — mints a one-time enrolment key.
* `network-tailscale-address` — pins a device's Tailscale IPv4 address.

Because the token is a host fact, including this role a second time in the
same play does nothing. The credential exchange happens only once.

| Variable | Default | Purpose |
|----------|---------|---------|
| `tailscale_api_base` | `https://api.tailscale.com/api/v2` | API root |

Both API calls are `no_log`.

## OAuth scopes

The OAuth client needs one scope per operation it performs. `auth_keys`
covers key generation. **Setting a device's address also needs
`devices:core`, with write access** (Tailscale Admin Console, under
Settings → OAuth clients). If a client lacks the scope, the API call fails
with `403`.
