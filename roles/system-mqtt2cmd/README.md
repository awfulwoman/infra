# System MQTT2CMD

Installs a lightweight MQTT-driven command executor. A bash script subscribes to a host-specific MQTT topic and executes system commands in response to received payloads. Runs as a persistent systemd service.

## Supported Commands

Messages published to `<basetopic>/<hostname>` trigger the following actions:

| Payload | Action |
|---|---|
| `shutdown` | Immediate shutdown |
| `suspend` | System suspend |
| `reboot` | Reboot |
| `ansiblepull` | Runs the ansible-pull script as the Ansible user |
| `restart zigbee2mqtt` | Restarts the zigbee2mqtt Docker container |
| `restart torrents` | Restarts the qbittorrent Docker container |
| `restart downloads` | Restarts the downloads Docker Compose stack |

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `mqtt2cmd_broker` | `mqtt.<domainname_infra>` | MQTT broker hostname |
| `mqtt2cmd_basetopic` | `servers` | Topic prefix; full topic is `<basetopic>/<hostname>` |
| `mqtt2cmd_executable` | `mqtt2cmd` | Script filename |
| `mqtt2cmd_executable_path` | `/usr/local/sbin` | Deployment path for the script |

## Design Notes

The script runs `mosquitto_sub` in an infinite outer loop so it automatically reconnects after broker disconnections or network drops (with a 10-second delay between reconnect attempts).

Shutdown, suspend, reboot, and ansible-pull commands require privilege escalation. Rather than a broad sudoers grant, the role creates targeted passwordless sudo rules for only the specific binaries needed (`/usr/sbin/shutdown`, `/usr/bin/systemctl hibernate`, `/usr/sbin/reboot`). The ansible-pull command uses `runuser` which doesn't require sudo.

The service uses `TERM=dumb` to prevent terminal control issues in a non-interactive systemd context.
