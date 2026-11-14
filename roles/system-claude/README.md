# system-claude

Installs the Claude Code CLI and configures the shell environment for it.

## What it does

- Installs OS dependencies (macOS via Homebrew, Ubuntu via apt)
- Installs the Claude CLI via the official install script to `~/.local/bin/claude`
- Makes sure that `~/.local/bin` is on `PATH` in the user's shell profile
- Creates the Claude config directory (`CLAUDE_CONFIG_DIR`)
- Exports Claude-related environment variables (model, feedback survey, prompt suggestion, config dir)
  into `.zshenv` on macOS, and removes any stale copies from `.zshrc`
- Enables tmux mouse mode for scrollback
- Optionally (`system_claude_agentmemory`) connects Claude Code to agentmemory, see below

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

zsh sources `.zshrc` only for **interactive** shells. Anything launched
outside an interactive terminal cannot see exports placed there: GUI
launches, launchd agents, and non-interactive shells. Because of this,
`CLAUDE_CONFIG_DIR` went unset, and Claude Code silently fell back to
`~/.claude` instead of `~/.config/claude`. This produced two divergent config
directories.

zsh sources `.zshenv` on every invocation, so the variable applies no matter
how Claude Code starts. zsh reads `.zshenv` before `.zshrc`, so the role also
strips these exports from `.zshrc`. If one stays there, it overrides the value
and reintroduces the split.

## Platforms

- Ubuntu/Debian
- macOS

## agentmemory

Off by default; camina enables it. When on, the role:

- installs the `@agentmemory/mcp` stdio shim globally with nvm's npm (so `system-nvm` must run first)
- writes `~/.config/claude/agentmemory.env` (mode 0600) with `AGENTMEMORY_URL` and `AGENTMEMORY_SECRET`
- writes the wrapper `~/.local/bin/claude-agentmemory`, which sources that file and execs the real `claude`, and points `alias claude=` at it in `.bashrc`
- registers the MCP server at user scope with `claude mcp add-json`. The entry holds the URL and `${AGENTMEMORY_SECRET}`, never the value, so the secret is not in `.claude.json`. It is re-registered when the URL changes.

The secret must not go in `system_claude_environment`: on Ubuntu that is `/etc/environment`, which any local user can read.

Running `~/.local/bin/claude` directly, or a non-interactive shell, starts Claude Code without the secret, so the MCP server fails to authenticate. Use the alias or the wrapper.

Variables: `system_claude_agentmemory`, `_url`, `_secret` (vault), `_version` (keep in step with `composition-agentmemory`), `_env_file`, `system_claude_wrapper_path`.

### Session capture (manual)

The official plugin adds hooks that record prompts and tool calls. Installing it is interactive: `/plugin marketplace add rohitg00/agentmemory`, then `/plugin install agentmemory@agentmemory`, leaving the URL and secret options empty. Hooks then read `AGENTMEMORY_URL` and `AGENTMEMORY_SECRET` from the wrapper's environment (untested). The plugin's bundled MCP bridge ignores the env var; disable it so tools are not registered twice.
