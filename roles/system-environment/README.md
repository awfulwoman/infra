# system-environment

Sets persistent environment variables on Debian (via `/etc/environment`) and macOS (via `~/.zshenv`). Pass a dict of key/value pairs as `environment_config`. Override the target file with `environment_file`.

Used by other roles (e.g. `bootstrap-macos-server`) to inject host-level environment variables in a cross-platform way.
