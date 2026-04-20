# System Docker

Installs and configures Docker CE from the official Docker repository on Debian or Ubuntu hosts. Handles the full installation lifecycle: adds the appropriate apt repository for the detected distro and architecture, installs Docker CE with the Compose plugin, adds the Ansible user to the `docker` group, and deploys daemon and service configuration.

## Configuration

The daemon is configured to listen on both the Unix socket (`/var/run/docker.sock`) and TCP port 2375 (`daemon.json`). A systemd override (`docker.service.d/override.conf`) ensures Docker reads from the config file rather than relying on inline flags — this is necessary because Docker's own service unit sets `ExecStart` flags that conflict with the daemon config file.

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `docker_port_open` | `false` | When true, installs a UFW application profile to open TCP 2375 in the firewall |

## Design Notes

TCP socket exposure is intentional for remote Docker API access over Tailscale. The `docker_port_open` flag is a host-level opt-in — most hosts don't need the port open in UFW, but hosts that do (e.g. those accessed by Portainer or remote tooling) can enable it.

Architecture detection handles both `x86_64` → `amd64` and `aarch64` → `arm64` mappings for the apt repo.
