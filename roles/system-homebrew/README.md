# system-homebrew

This role installs [Homebrew](https://brew.sh/) on macOS (Apple Silicon and
Intel) and Linux, then installs a list of formulae. It handles
architecture-specific binary paths automatically. On Linux, it installs
build prerequisites through apt and configures `shellenv` in `~/.bashrc`.

During installation, the role adds a temporary passwordless sudo rule. It
always removes the rule afterward.
