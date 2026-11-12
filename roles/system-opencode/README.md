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

## Permissions

`opencode.jsonc` carries an ordered `permissions` list (opencode v2, last match
wins): ask for `shell` and `external_directory` by default, then allow the
commands in `system_opencode_shell_allow`. `system_opencode_permissions_extra`
is appended last, for hard denies such as `git push *`.

Note: `~/.config/opencode/cli.json` can set `session.permissions: autoaccept`,
which accepts every request and makes the `ask` rules moot.

## Quota display (opencode-quota)

`system_opencode_plugins` loads `@slkiser/opencode-quota`, which shows Ollama
Cloud session and weekly quota. It needs Node 22.13+ only for its terminal
commands (`system-nvm` provides it). `system_opencode_quota_settings` writes the
plugin's `settings.jsonc` with a custom provider that reads
`<ollama url>/api/balance`. Malcolm's Ollama signs cloud requests with its own
sign-in, so no API key is needed; the plugin only requires HTTPS and *a*
bearer key, so `ollama.<domain>` (Traefik on camina) and a placeholder key do
the job. Changes saved from the TUI's quota settings are overwritten on the
next run.

## agentmemory

Connects [composition-agentmemory](../composition-agentmemory/README.md)
(`https://agentmemory.<domain>`) to opencode in two ways:

- **MCP:** `mcp.servers.agentmemory` runs the `@agentmemory/mcp` stdio shim
  (via nvm's Node), proxying to the server for the full tool set.
- **Plugin:** `agentmemory-capture.ts` in `~/.config/opencode/plugins/`
  auto-captures session activity, plus `/recall` and `/remember` in
  `commands/`. Fetched from the upstream tag with pinned checksums. Do not also
  list it under `plugins` in `opencode.jsonc`, or it captures every event twice.

The URL and bearer secret (`vault_composition_agentmemory_secret`) go in
`~/.config/opencode/agentmemory.env` (mode 0600), which the wrapper exports. A
bare run of the Homebrew binary therefore has no memory. The plugin sends what
the agent sees and does to that server. Keep `system_opencode_agentmemory_version`
in step with the composition's image tag, and update the checksums with it.

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

- `system_opencode_ollama_base_url`: OpenAI-compatible endpoint, defaults to `llm_default_openai_uri` (`https://ollama.<domain>/v1`)
- `system_opencode_sandbox*`: sandbox switches and paths, see above
- `system_opencode_cli_config`: CLI settings (e.g. keybinds) applied via the wrapper
- `system_opencode_permissions_default`, `_shell_allow`, `_extra`: permission rules, see above
- `system_opencode_agentmemory*`: agentmemory URL, secret, version and fetched files
- `system_opencode_model`: optional default model, `provider/model` (e.g. `ollama/kimi-k3:cloud`)

## Platforms

- Ubuntu/Debian
- macOS

## gateway

Registers the gateway MCP server (`https://gateway.<domain>/mcp`: email, calendar, notes, bookmarks, reminders) as a `remote` server in `opencode.jsonc`.

- opencode has its own client token, `vault_gateway_mcp_token_opencode`, listed as `opencode` in `composition_gateway_server_auth_clients`. It can be revoked without touching Claude's or Jarvis's tokens. Deploy `composition-gateway` after adding or rotating it.
- The config holds `Bearer {env:GATEWAY_MCP_TOKEN}`, never the value. The token is written to `~/.config/opencode/gateway.env` (mode 0600), which the wrapper sources.
- Variables: `system_opencode_gateway` (on/off), `_url`, `_token`, `_env_file`.
- As with agentmemory, running the Homebrew binary directly skips the wrapper, so the token is not set and the server fails to authenticate.

## searxng

Registers the SearXNG MCP server (`https://searchmcp.<domain>/mcp`, from `composition-mcp-searxng`) as a `remote` server, for web search. The service has a single shared bearer token (`vault_mcp_searxng_auth_token`), so unlike the gateway it cannot be revoked per client. The token goes in `~/.config/opencode/searxng.env` (mode 0600), sourced by the wrapper; the config holds `Bearer {env:SEARXNG_MCP_TOKEN}`.

Variables: `system_opencode_searxng` (on/off), `_url`, `_token`, `_env_file`.

## github (push + gh via a GitHub App)

Lets the agent push to the awfulwoman repos and drive `gh` without ever
reading a long-lived credential. A GitHub App installation token (1 hour) is
minted on demand; git and gh use it, and the App's private key is denied to the
sandbox.

- `~/.config/opencode/github-app.pem` holds the App private key (mode 0600,
  from `vault_github_app_private_key`). It is in `system_opencode_sandbox_deny`,
  so the agent cannot read it.
- `mint-github-token.sh` signs a JWT with that key and POSTs to
  `api.github.com` for an installation token. The wrapper runs it (outside the
  sandbox) to set `GH_TOKEN`/`GITHUB_TOKEN` for `gh`, and a git credential
  helper reuses `GH_TOKEN` for pushes. The token lasts an hour, so a session
  older than that pushes with an expired token until it is restarted; only the
  wrapper can mint a fresh one because the key is sandbox-denied.
- Git is pointed at HTTPS via `url.*.insteadOf` in the wrapper, so the agent
  pushes over HTTPS with `x-access-token` + the minted token; the SSH remotes
  are left untouched for manual use.
- The App needs `Contents: read/write` (git) and `Issues: read/write` (`gh`),
  installed on the repos it should reach.

To enable (once the App exists):

1. Create a GitHub App owned by the account, install it on the repos, note its
   App ID and installation ID.
2. `ansible-vault`-encrypt the App's private key as
   `vault_github_app_private_key`, and the IDs as `vault_github_app_id` and
   `vault_github_app_installation_id` (all in `vault_external_github.yaml`).
3. Set `system_opencode_github: true`.

Variables: `system_opencode_github` (on/off, default off), `_app_id`,
`_installation_id`, `_app_key_file`, `_mint_helper`, `_credential_helper`.
