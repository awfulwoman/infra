# System Pipx

Installs [pipx](https://pipx.pypa.io/) and manages Python CLI applications in isolated virtual environments. If pipx is not already present, bootstraps it via a temporary venv rather than relying on the system package manager (which may provide an outdated version). Then installs all packages listed in `system_pipx_packages`.

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `system_pipx_packages` | `[]` | List of pipx package names to install |

Packages are specified as plain names (e.g. `ansible-lint`, `httpie`) and installed with `--include-deps` to ensure CLI entry points from dependencies are also available.

## Design Notes

The bootstrap process creates a temporary venv at `/tmp/bootstrap`, uses it to install pipx, then uses that pipx to install pipx into the user's own environment (`~/.local/bin/pipx`). The temporary venv is deleted afterwards. This avoids the chicken-and-egg problem of needing pipx to install pipx cleanly without depending on distro packages.

The presence check targets `~/.local/bin/pipx` directly, so the bootstrap block is skipped entirely on subsequent runs.
