# Virtual Hetzner

Configures a Hetzner Cloud VM to bind a floating IP address to its primary network interface using netplan.

Hetzner floating IPs are not automatically configured on the OS level — the VM only knows about its primary IP from DHCP. This role adds a netplan configuration file that assigns the floating IP as an additional address on `eth0`, making it reachable after a netplan apply.

## Required Variables

| Variable | Description |
|---|---|
| `hetzner_floating_ip` | The floating IP address to bind (e.g., `1.2.3.4`) |

## Design Notes

- The netplan config is written to `/etc/netplan/60-floating-ip.yaml` with a high sort priority so it applies after the primary interface config.
- The config uses the `networkd` renderer and applies a `/32` prefix to the floating IP, which is correct for Hetzner's single-host floating IPs.
- A handler applies netplan non-interactively on change.
- This role pairs with the `infra-hetzner` Terraform role which provisions the floating IP resource itself.
