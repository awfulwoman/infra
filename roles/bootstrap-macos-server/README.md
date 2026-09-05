# Bootstrap macOS Server

This role does the first-time setup for a macOS server, currently host-malcolm, a Mac Mini. It applies common environment variables through `system-environment`, patches `.zshrc` for a terminal compatibility issue, and removes default consumer apps that a headless server does not need.

## What it does

- Applies `system-environment` for consistent shell environment variables.
- Adds a `.zshrc` block that remaps the `TERM` variable from `xterm-256color-ghostty` to `xterm-256color` for SSH connections from the Ghostty terminal. Without this, many CLI tools render incorrectly, because they do not recognize the Ghostty terminfo entry.
- Removes GarageBand, iMovie, Keynote, Numbers, and Pages. These large apps use disk space and serve no purpose on a server.

## Dependencies

This role depends on `system-homebrew`, declared in `meta/main.yaml`. This makes sure that Homebrew is available before the role runs, because later roles on this host use it.
