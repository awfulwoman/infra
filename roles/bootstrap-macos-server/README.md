# Bootstrap macOS Server

Performs essential first-time setup for a macOS server (currently host-malcolm, a Mac Mini). Applies common environment variables via `system-environment`, patches `.zshrc` to work around a terminal compatibility issue, and removes default consumer apps that have no place on a headless server.

## What it does

- Applies `system-environment` for consistent shell environment variables.
- Adds a `.zshrc` block that remaps the `TERM` variable from `xterm-256color-ghostty` to `xterm-256color` when connecting over SSH from the Ghostty terminal. Without this, many CLI tools fail to render correctly because they don't recognise the Ghostty terminfo entry.
- Removes GarageBand, iMovie, Keynote, Numbers, and Pages — large apps that consume disk and serve no purpose on a server.

## Dependencies

Depends on `system-homebrew` (declared in `meta/main.yaml`) to ensure Homebrew is available before this role runs, as subsequent roles on this host will use it.
