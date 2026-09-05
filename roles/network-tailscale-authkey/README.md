# network-tailscale-authkey

This role generates a short-lived Tailscale one-time auth key. It exposes the key as the `tailscale_authkey` Ansible fact, for later roles in the same play. The role delegates the OAuth credential exchange to [`network-tailscale-token`](../network-tailscale-token/README.md). It then calls the Tailscale keys API to issue a pre-authorized, non-reusable key, tagged with `tailscale_node_tags`.

The key expires after `tailscale_authkey_expiry_seconds` (default `300`). All API calls use `no_log`.
