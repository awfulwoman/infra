# Apple Hardware

Manages hardware radio state on macOS hosts — specifically WiFi and Bluetooth. The role toggles WiFi through `networksetup` and Bluetooth through [`blueutil`](https://github.com/toy/blueutil), installed automatically through Homebrew. Both are idempotent: the role checks the current state before it issues any change command. Requires the `system-homebrew` role (declared as a dependency in `meta/main.yaml`).

## Variables

| Variable | Default | Description |
|---|---|---|
| `hardware_apple_bluetooth` | `true` | Whether the role enables Bluetooth |
| `hardware_apple_wifi` | `true` | Whether the role enables WiFi |
| `hardware_apple_wifi_interface` | `null` | macOS network interface name (for example `en0`). The role skips WiFi tasks when this is `null` |

## Notes

- Homebrew installs `blueutil`. The role derives the binary path from `system_homebrew_bin`, provided by `system-homebrew`.
- WiFi management requires the interface name. Set `hardware_apple_wifi_interface` in `host_vars` for the target host (typically `en0` on Mac Minis).
- This role is idempotent. It reads the current state before it issues any change, so repeated runs do not produce spurious changes.
