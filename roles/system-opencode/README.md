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

## Variables

See `defaults/main.yaml`.

- `system_opencode_ollama_base_url`: OpenAI-compatible endpoint, defaults to `llm_default_openai_uri`
- `system_opencode_model`: optional default model, `provider/model` (e.g. `ollama/kimi-k3:cloud`)

## Platforms

- Ubuntu/Debian
- macOS
