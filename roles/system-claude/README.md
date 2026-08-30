# system-claude

Installs the Claude Code CLI and configures the shell environment for it.

## What it does

- Installs OS dependencies (macOS via Homebrew, Ubuntu via apt)
- Installs the `gh` GitHub CLI
- Installs the Claude CLI via the official install script to `~/.local/bin/claude`
- Ensures `~/.local/bin` is on `PATH` in the user's shell profile
- Creates the Claude config directory (`CLAUDE_CONFIG_DIR`)
- Exports Claude-related environment variables (model, feedback survey, prompt suggestion, config dir)
  into `.zshenv` on macOS, and removes any stale copies from `.zshrc`
- Enables tmux mouse mode for scrollback

## Variables

See `defaults/main.yaml`. Key variables:

- `system_claude_install_url`: Claude CLI install script URL
- `system_claude_channel`: release channel (`stable`, `latest`, or a version)
- `system_claude_ensure_path`: whether to add `~/.local/bin` to `PATH`
- `system_claude_profile_file`: shell profile edited for `PATH` (`.zshrc` on macOS, `.bashrc` on Ubuntu)
- `system_claude_env_file`: file receiving the environment variables (`.zshenv` on macOS)
- `system_claude_environment`: dict of environment variables to export
- `system_claude_settings_path`: Claude config directory
- `system_claude_settings_group`: group owner for the settings directory (`staff` on macOS)

## Why `.zshenv` on macOS

zsh sources `.zshrc` only for **interactive** shells. Exports placed there are
invisible to anything launched outside an interactive terminal — GUI launches,
launchd agents, non-interactive shells — so `CLAUDE_CONFIG_DIR` went unset and
Claude Code silently fell back to `~/.claude` instead of `~/.config/claude`,
producing two divergent config directories.

`.zshenv` is sourced by every zsh invocation, so the variable applies however
Claude Code is started. Because `.zshenv` is read *before* `.zshrc`, the role
also strips these exports from `.zshrc`; leaving one there would override the
value and reintroduce the split.

## Platforms

- Ubuntu/Debian
- macOS
