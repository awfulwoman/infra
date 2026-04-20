# System Wake-on-LAN

Configures a network interface to accept Wake-on-LAN magic packets by deploying a systemd service that runs `ethtool` at boot.

WoL is disabled by default on most NICs after each boot. This role solves that by creating a `oneshot` systemd service that re-enables it on every start-up. Combined with `system-sleepuntil`, a host can be suspended overnight and woken remotely by sending a magic packet to its MAC address.

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `wakeonlan_interface` | `enp3s0` | Network interface to enable WoL on |
| `wakeonlan_destination_path` | `/etc/systemd/system` | Where the service unit file is written |
| `wakeonlan_destination_filename` | `wol.service` | Service unit filename |
| `wakeonlan_destination_owner` | `root` | File owner |
| `wakeonlan_destination_group` | `root` | File group |

## Design Notes

- `wakeonlan_interface` must be set per-host in `host_vars` since interface names vary by hardware.
- The service uses `RemainAfterExit=yes` so systemd considers it "active" after the one-shot command completes.
- WoL only functions if it is also enabled in the host's BIOS/UEFI firmware — Ansible cannot configure that.
