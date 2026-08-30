# system-colima

Installs and configures [Colima](https://github.com/abiosoft/colima) as a
background container runtime on macOS, giving the host a Docker daemon without
Docker Desktop.

## What it does

- Installs `colima`, `docker` and `docker-compose` via Homebrew.
- Removes any `brew services` (`homebrew.mxcl.colima`) LaunchAgent.
- Deploys a per-user `launchd` LaunchAgent (`com.awfulwoman.colima`) that runs
  `colima start --foreground` with the configured VM resources, so the VM comes
  up at login and is restarted if it exits uncleanly.
- Writes `DOCKER_HOST` into `~/.zshenv` so the `docker` CLI and Ansible's
  `community.docker` modules reach the Colima socket without an active context.
- Waits for `~/.colima/default/docker.sock` and confirms `colima status`.

## Variables

See `defaults/main.yaml`:

| Variable | Default | Description |
|---|---|---|
| `system_colima_cpu` | `4` | vCPUs for the VM |
| `system_colima_memory` | `8` | VM memory (GiB) |
| `system_colima_disk` | `60` | VM disk (GiB) — cannot be shrunk later |
| `system_colima_vm_type` | `vz` | `vz` (native, macOS 13+) or `qemu` |
| `system_colima_rosetta` | `true` | Rosetta 2 for x86_64 images (vz only) |
| `system_colima_mount_type` | `virtiofs` | `virtiofs`, `sshfs` or `9p` |
| `system_colima_cpu_type` | `host` | CPU model exposed to the guest |
| `system_colima_runtime` | `docker` | Container runtime inside the VM |
| `system_colima_set_docker_host` | `true` | Manage `DOCKER_HOST` in `~/.zshenv` |
| `system_colima_launchd_label` | `com.awfulwoman.colima` | LaunchAgent label |

## Notes

- The LaunchAgent runs at **login**, not boot. The host must auto-login for the
  VM to come up after a reboot.
- VM config is driven entirely by the `colima start` flags in the plist, not by
  `~/.colima/default/colima.yaml`; change a variable and re-run to apply it (the
  plist change reloads the agent).
- Ansible over SSH gets a bare `PATH`, so the plist sets `PATH` and `HOME`
  explicitly for `colima`/`limactl`.

## Platforms

- macOS (launchd). No-op on other platforms.
