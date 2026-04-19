# system-homebrew

Installs [Homebrew](https://brew.sh/) on macOS (Apple Silicon and Intel) and Linux, then installs a list of formulae. Handles architecture-specific binary paths automatically. On Linux, installs build prerequisites via apt and configures `shellenv` in `~/.bashrc`.

During installation a temporary passwordless sudo rule is added and unconditionally removed afterwards.
