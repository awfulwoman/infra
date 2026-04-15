# system-claude

Installs the Claude Code CLI and configures the shell environment for it.

## What it does

- Installs OS dependencies (macOS via Homebrew, Ubuntu via apt)
- Installs the `gh` GitHub CLI
- Installs the Claude CLI via the official install script to `~/.local/bin/claude`
- Ensures `~/.local/bin` is on `PATH` in the user's shell profile
- Creates the Claude config directory (`CLAUDE_CONFIG_DIR`)
- Exports Claude-related environment variables (model, feedback survey, prompt suggestion, config dir)
- Enables tmux mouse mode for scrollback

## Variables

See `defaults/main.yaml`. Key variables:

- `system_claude_install_url`: Claude CLI install script URL
- `system_claude_channel`: release channel (`stable`, `latest`, or a version)
- `system_claude_ensure_path`: whether to add `~/.local/bin` to `PATH`
- `system_claude_profile_file`: shell profile to edit (`.zshrc` on macOS, `.bashrc` on Ubuntu)
- `system_claude_settings_path`: Claude config directory
- `system_claude_settings_group`: group owner for the settings directory (`staff` on macOS)

## Platforms

- Ubuntu/Debian
- macOS
