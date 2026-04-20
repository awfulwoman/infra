# Zigbee ConBee II

Creates stable `/dev/zigbee-*` symlinks for Dresden Elektronik ConBee II Zigbee USB sticks via a udev rule. Without this, the device appears as a generic `/dev/ttyUSBx` path that can change across reboots or when other USB serial devices are present.

Two devices are registered by serial number:

| Symlink | Serial | Purpose |
|---|---|---|
| `/dev/zigbee-core` | `DE2467569` | Primary Zigbee coordinator |
| `/dev/zigbee-aqara` | `DE2652549` | Secondary coordinator (Aqara devices) |

The symlinks use the ConBee II USB vendor/product IDs (`1cf1:0030`) combined with the device serial number to ensure each stick always maps to the same path regardless of plug order.

## Notes

- The udev rule is deployed to `/etc/udev/rules.d/10-local.rules`.
- Docker Compose services (e.g. deCONZ, Zigbee2MQTT) reference these stable symlinks so container device mounts don't break when USB is re-enumerated.
- To add a new dongle, find its serial with `udevadm info -a /dev/ttyUSBx | grep serial` and add a new rule line with a new symlink name.
