# Apple Hardware

Manages hardware radio state on macOS hosts — specifically WiFi and Bluetooth. WiFi is toggled via `networksetup`, Bluetooth via [`blueutil`](https://github.com/toy/blueutil) (installed automatically via Homebrew). Both are idempotent: the current state is checked before issuing any change command. Requires the `system-homebrew` role (declared as a dependency in `meta/main.yaml`).

## Variables

| Variable | Default | Description |
|---|---|---|
| `hardware_apple_bluetooth` | `true` | Whether Bluetooth should be enabled |
| `hardware_apple_wifi` | `true` | Whether WiFi should be enabled |
| `hardware_apple_wifi_interface` | `null` | macOS network interface name (e.g. `en0`). WiFi tasks are skipped when `null` |

## Notes

- `blueutil` is installed from Homebrew; the binary path is derived from `system_homebrew_bin` (provided by `system-homebrew`).
- WiFi management requires knowing the interface name. Set `hardware_apple_wifi_interface` in `host_vars` for the target host (typically `en0` on Mac Minis).
- This role is idempotent — it reads current state before issuing any change, so repeated runs don't produce spurious changes.
