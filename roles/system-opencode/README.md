# system-opencode

Configures the [opencode](https://opencode.ai) CLI to use Ollama on malcolm.

opencode itself is installed by `system-homebrew` (`system_homebrew_formulae`).
This role only writes its user config, `~/.config/opencode/opencode.json`.

## What it does

- Creates `~/.config/opencode/`
- Renders `opencode.jsonc` in the native opencode v2 format, pointing the
  built-in `ollama` provider at malcolm (`providers.ollama.settings.baseURL`)
- Removes the legacy `opencode.json`, which opencode would otherwise merge in

opencode v2 discovers models from Ollama and reads their context size, vision
and tool support, so no model list is kept here. `*:cloud` models are proxied by
Ollama on malcolm to Ollama Cloud, using malcolm's own sign-in. Models without
the `tools` capability cannot drive opencode's edit and shell tools.

## Sandbox (nono)

opencode runs inside a [nono](https://github.com/nolabs-ai/nono) Landlock
sandbox, installed by `system-homebrew` (`nono` in `system_homebrew_formulae`).

- `nono pull nolabs-ai/opencode` installs the base pack
- `~/.config/nono/profiles/opencode-local.jsonc` extends it with
  `system_opencode_sandbox_allow` (read+write, default `$HOME/Code`),
  `_read` and `_deny`. The current directory is always granted. Network is
  unrestricted.
- `~/.local/bin/opencode` is a wrapper that runs
  `nono run --profile opencode-local -- opencode --standalone`, and an alias in
  `.bashrc` points `opencode` at it (Homebrew's `shellenv` would otherwise
  shadow it on PATH)
- The wrapper also sets `OPENCODE_CLI_CONFIG_CONTENT` from `system_opencode_cli_config`
  (default: `app.exit` without `ctrl+c`). opencode merges it over `cli.json`, which
  the TUI rewrites, so Ansible owns only these keys
- Admin commands (`serve`, `auth`, `acp`, `service`, `models`, ...) bypass the
  sandbox, since they do not support `--standalone`

`--standalone` matters: opencode v2 normally hands work to a background server
that nono cannot contain. The wrapper is a convenience, not enforcement: the
Homebrew binary can still be run directly.

The pack disables project-level `opencode.json`, `AGENTS.md` and plugins
(`OPENCODE_DISABLE_PROJECT_CONFIG=1`). Only global config applies.

Check with `nono profile show opencode-local` and, inside a session,
`nono why`. Set `system_opencode_sandbox: false` to skip all of this.

## Variables

See `defaults/main.yaml`.

- `system_opencode_ollama_base_url`: OpenAI-compatible endpoint, defaults to `llm_default_openai_uri`
- `system_opencode_sandbox*`: sandbox switches and paths, see above
- `system_opencode_cli_config`: CLI settings (e.g. keybinds) applied via the wrapper
- `system_opencode_model`: optional default model, `provider/model` (e.g. `ollama/kimi-k3:cloud`)

## Platforms

- Ubuntu/Debian
- macOS
