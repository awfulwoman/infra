# Zigbee ConBee II

This role creates stable `/dev/zigbee-*` symlinks for Dresden Elektronik ConBee II Zigbee USB sticks, through a udev rule. Without this rule, the device appears as a generic `/dev/ttyUSBx` path. That path can change across reboots, or when other USB serial devices are present.

Two devices are registered by serial number:

| Symlink | Serial | Purpose |
|---|---|---|
| `/dev/zigbee-core` | `DE2467569` | Primary Zigbee coordinator |
| `/dev/zigbee-aqara` | `DE2652549` | Secondary coordinator (Aqara devices) |

The symlinks combine the ConBee II USB vendor/product IDs (`1cf1:0030`) with the device serial number. This way, each stick always maps to the same path, no matter the plug order.

## Notes

- The role deploys the udev rule to `/etc/udev/rules.d/10-local.rules`.
- Docker Compose services (for example deCONZ and Zigbee2MQTT) reference these stable symlinks, so container device mounts do not break when USB devices are re-enumerated.
- To add a new dongle, find its serial with `udevadm info -a /dev/ttyUSBx | grep serial`, then add a new rule line with a new symlink name.
