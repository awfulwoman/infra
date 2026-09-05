# System Wake-on-LAN

Configures a network interface to accept Wake-on-LAN magic packets. The role deploys a systemd service that runs `ethtool` at boot.

WoL is disabled by default on most NICs after each boot. This role solves that. It creates a `oneshot` systemd service that re-enables WoL on every start-up. With `system-sleepuntil`, you can suspend a host overnight and wake it remotely with a magic packet sent to its MAC address.

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `wakeonlan_interface` | `enp3s0` | Network interface to enable WoL on |
| `wakeonlan_destination_path` | `/etc/systemd/system` | Where the service unit file is written |
| `wakeonlan_destination_filename` | `wol.service` | Service unit filename |
| `wakeonlan_destination_owner` | `root` | File owner |
| `wakeonlan_destination_group` | `root` | File group |

## Design Notes

- You must set `wakeonlan_interface` per host in `host_vars`, since interface names vary by hardware.
- The service uses `RemainAfterExit=yes` so systemd considers it "active" after the one-shot command completes.
- The host's BIOS/UEFI firmware must also enable WoL. Ansible cannot configure this setting.
