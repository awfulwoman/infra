# system-ollama

Installs and configures [Ollama](https://ollama.com/) as a background service, and pulls a configurable list of models.

## What it does

- **Ubuntu/Debian**: installs Ollama via the official `install.sh` script and manages it as a systemd service. Deploys a systemd drop-in (`override.conf`) for environment variables.
- **macOS**: installs Ollama via Homebrew and manages it as a per-user `launchd` LaunchAgent (`com.awfulwoman.ollama`).
- Waits for the Ollama API (`127.0.0.1:11434`) to be ready.
- Pulls each model listed in `system_ollama_models`.

## Variables

See `defaults/main.yaml`:

- `system_ollama_models`: list of model names to pull (e.g. `["llama3", "qwen2.5"]`). Empty by default.
- `system_ollama_env`: dict of environment variables passed to the Ollama service (e.g. `OLLAMA_HOST`, `OLLAMA_KEEP_ALIVE`, `OLLAMA_MODELS`).
- `system_ollama_bin`: path to the `ollama` binary. Defaults to the platform-appropriate Homebrew/`/usr/local/bin` path.

## Platforms

- Ubuntu/Debian (systemd)
- macOS (launchd)
