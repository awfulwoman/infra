# system-environment

This role sets persistent environment variables on Debian, through
`/etc/environment`, and macOS, through `~/.zshenv`. Pass a dict of key/value
pairs as `environment_config`. Override the target file with
`environment_file`.

Other roles, for example `bootstrap-macos-server`, use this role to inject
host-level environment variables in a cross-platform way.
