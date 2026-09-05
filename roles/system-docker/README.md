# System Docker

This role installs and configures Docker CE from the official Docker
repository, on Debian or Ubuntu hosts. It adds the correct apt repository for
the detected distro and architecture. It installs Docker CE with the Compose
plugin. It adds the Ansible user to the `docker` group. It also deploys the
daemon and service configuration.

## Configuration

The role configures the daemon to listen on both the Unix socket
(`/var/run/docker.sock`) and TCP port 2375, through `daemon.json`. A systemd
override (`docker.service.d/override.conf`) makes sure that Docker reads from
the config file instead of the inline flags. This override is necessary
because Docker's own service unit sets `ExecStart` flags that conflict with
the daemon config file.

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `docker_port_open` | `false` | When true, installs a UFW application profile to open TCP 2375 in the firewall |

## Design Notes

TCP socket exposure is intentional. It allows remote Docker API access over
Tailscale. The `docker_port_open` flag is a host-level opt-in. Most hosts do
not need the port open in UFW. Hosts that Portainer or other remote tools
access can enable it.

Architecture detection maps `x86_64` to `amd64` and `aarch64` to `arm64` for
the apt repo.
