# system-aw-deploy

Installs `aw-deploy` (CLI) and `aw-deploy-mcp` (stdio MCP server) so that agents
and scripts on this host can trigger Ansible playbook runs from the local infra
repo checkout.

## Requirements

- macOS only
- `uv` installed via Homebrew (this role installs it if absent)
- `~/Code/awfulwoman/infra` cloned with vault password configured

## Variables

| Variable | Default | Description |
|---|---|---|
| `system_aw_deploy_install_dir` | `/usr/local/bin` | Where to install the binaries |
| `system_aw_deploy_opt_dir` | `{{ awfulwoman_opt_dir }}/aw-deploy` | Working dir for venv |
| `system_aw_deploy_venv_dir` | `{{ system_aw_deploy_opt_dir }}/venv` | Python venv path |
| `system_aw_deploy_infra_dir` | `~/Code/awfulwoman/infra` | Infra repo location |
| `system_aw_deploy_state_dir` | `~/.local/state/aw-deploy` | Run logs location |

## Usage

```bash
aw-deploy run playbooks/hosts/apple-macmini-m4-16gb-malcolm/compositions.yaml --tags homeassistant
aw-deploy run playbooks/hosts/apple-macmini-m4-16gb-malcolm/core.yaml --check
aw-deploy list
aw-deploy logs --tail 3
```

## MCP registration

The binary alone is not enough — Claude Code also needs the server registered in
`~/.claude.json`. This is handled by the chezmoi `modify_dot_claude.json` script in the
dotfiles repo, which detects the binary and merges the entry automatically on `chezmoi apply`.
