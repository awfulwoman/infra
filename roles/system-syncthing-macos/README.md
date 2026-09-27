# system-syncthing-macos

This role runs [Syncthing](https://syncthing.net/) natively on macOS. It
installs Syncthing through Homebrew and runs it under a per-user LaunchAgent
(`com.awfulwoman.syncthing`) rather than `brew services`, which can't set the
environment it needs.

Devices, folders and the web UI login are set centrally from camina by
[`system-syncthing-config`](../system-syncthing-config).

## Why native, not colima

Apps on the Mac, such as desktop Obsidian (`system-obsidian-desktop`), work on
the synced folders directly. They need a real filesystem with working
file-change events. A bind mount into the colima VM doesn't provide that.

## Variables

| Variable | Default | Description |
|---|---|---|
| `syncthing_folder_root` | *(required, host_vars)* | Root for declared folders. Must be outside `~/Documents`, `~/Desktop` and `~/Downloads`, because TCC blocks launchd agents there |
| `system_syncthing_macos_gui_address` | `https://0.0.0.0:8384` | Syncthing serves its own self-signed TLS here, so camina can reach it |
| `system_syncthing_macos_api_key` | `vault_syncthing_api_key` | `STGUIAPIKEY` |

The host's `syncthing_api_url` and `syncthing_api_validate_certs: false` tell
camina how to reach this instance.
