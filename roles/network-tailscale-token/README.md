# network-tailscale-token

Exchanges the Tailscale OAuth client credentials (`tailscale_oauth_client_id` /
`tailscale_oauth_client_secret`, both mapped from vault in
`inventory/group_vars/infra/core.yaml`) for a short-lived API bearer token, and
exposes it as the `tailscale_api_token` fact.

Every role in this repo that talks to the Tailscale API goes through here rather
than repeating the OAuth dance:

* `network-tailscale-authkey` — mints a one-time enrolment key.
* `network-tailscale-address` — pins a device's Tailscale IPv4 address.

Because the token is a host fact, including this role a second time in the same
play is a no-op — the credential exchange only happens once.

| Variable | Default | Purpose |
|----------|---------|---------|
| `tailscale_api_base` | `https://api.tailscale.com/api/v2` | API root |

Both API calls are `no_log`.

## OAuth scopes

The OAuth client needs a scope per operation it is used for. `auth_keys` covers
key generation; **setting a device's address additionally needs `devices:core`
with write access** (Tailscale Admin Console → Settings → OAuth clients). A
client missing the scope fails the API call with `403`.
