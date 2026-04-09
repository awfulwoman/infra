# system-claude: macOS Support Design

**Date:** 2026-04-09
**Status:** Approved

## Goal

Extend the `system-claude` Ansible role to support macOS (malcolm, a Mac Mini) alongside the existing Ubuntu setup.

## Approach

Split platform-specific tasks into separate include files, dispatched from `main.yaml` using `ansible_facts['os_family']`. This matches the established pattern in this repo (`system-ollama`). Shared tasks remain in `main.yaml`.

## File Structure

```
ansible/roles/system-claude/
  tasks/
    main.yaml           # dispatch block + shared tasks
    install-macos.yaml  # homebrew packages + gh
    install-ubuntu.yaml # apt packages + gh keyring (extracted from current main.yaml)
  defaults/
    main.yaml           # updated with neutral default for settings path
```

## Platform-Specific Tasks

### install-ubuntu.yaml

Extracts verbatim from current `main.yaml`:
- Install apt packages: `curl`, `gpg`, `yt-dlp`, `bubblewrap`, `socat`, `libonig-dev`
- Add GitHub CLI apt keyring
- Add GitHub CLI apt repository
- Install `gh` via apt

### install-macos.yaml

Installs via `community.general.homebrew`:
- `socat`, `yt-dlp`, `gh`

Omissions:
- `bubblewrap` — Linux sandbox tool, no macOS equivalent
- `libonig-dev` — apt-specific dev header, not needed on macOS
- `curl`, `gpg` — available by default on macOS

## Shared Tasks (main.yaml)

These tasks already work cross-platform and remain in `main.yaml`:
- Claude CLI install (curl | bash install script)
- `~/.local/bin` PATH export
- Settings directory creation
- Environment variable exports
- tmux mouse mode

All shared tasks are parameterised on `system_claude_profile_file` and `system_claude_settings_path`.

## Defaults

`defaults/main.yaml` changes:
- `system_claude_settings_path`: `/fastpool/claude/settings` → `~/.config/claude` (neutral cross-platform default)
- `system_claude_profile_file`: remains `.bashrc` (Ubuntu default; overridden per host)

## Host Variables

### host_vars/deedee/core.yaml (new entries)
```yaml
system_claude_settings_path: "/fastpool/claude/settings"
```

### host_vars/malcolm/core.yaml (new entries)
```yaml
system_claude_settings_path: "/opt/claude"
system_claude_profile_file: ".zshrc"
```

`vagrant-wrapper` inherits the `~/.config/claude` default — no override needed.

## Playbook Change

`ansible/playbooks/baremetal/malcolm/core.yaml` — add `system-claude` to the roles list.
