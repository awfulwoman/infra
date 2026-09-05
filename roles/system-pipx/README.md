# System Pipx

This role installs [pipx](https://pipx.pypa.io/) and manages Python CLI
applications in isolated virtual environments. If the host has no pipx, the
role bootstraps it through a temporary venv, rather than the system package
manager, which can provide an outdated version. Then it installs all
packages listed in `system_pipx_packages`.

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `system_pipx_packages` | `[]` | List of pipx package names to install |

List packages as plain names, for example `ansible-lint` or `httpie`. The
role installs them with `--include-deps`, to make sure that CLI entry points
from dependencies are also available.

## Design Notes

The bootstrap process creates a temporary venv at `/tmp/bootstrap`, and uses
it to install pipx. It then uses that pipx to install pipx into the user's
own environment (`~/.local/bin/pipx`). The role deletes the temporary venv
afterward. This avoids the circular problem of needing pipx to install pipx,
without depending on distro packages.

The presence check targets `~/.local/bin/pipx` directly, so later runs skip
the bootstrap block entirely.
