# network-tailscale-authkey

Generates a short-lived Tailscale one-time auth key and exposes it as the `tailscale_authkey` Ansible fact for use by subsequent roles in the same play. Delegates the OAuth credential exchange to [`network-tailscale-token`](../network-tailscale-token/README.md), then calls the Tailscale keys API to issue a pre-authorised, non-reusable key tagged with `tailscale_node_tags`.

The key expires after `tailscale_authkey_expiry_seconds` (default `300`). All API calls are `no_log`.
