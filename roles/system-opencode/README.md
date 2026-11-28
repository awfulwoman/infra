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
Ollama on malcolm to Ollama Cloud, using malcolm's own sign-in. The whole Ollama
Cloud catalogue is pulled into `system_ollama_models` in
`inventory/host_vars/apple-macmini-m4-16gb-malcolm/core.yaml`, where a new cloud
model is added; there is nothing to change here. Models without the `tools`
capability cannot drive opencode's edit and shell tools, and opencode only
offers models reporting the `completion` capability.

## Permissions

`opencode.jsonc` carries an ordered `permissions` list (opencode v2, last match
wins): ask for `shell` and `external_directory` by default, then allow the
commands in `system_opencode_shell_allow`. `system_opencode_permissions_extra`
is appended last, for hard denies such as `git push *`.

Note: `~/.config/opencode/cli.json` can set `session.permissions: autoaccept`,
which accepts every request and makes the `ask` rules moot.

## Ollama prices

Ollama's API publishes no prices, so [composition-ollama-pricing](../composition-ollama-pricing/README.md)
scrapes ollama.com once a day and serves the catalogue in opencode's model
shape. `~/.config/opencode/plugins/ollama-cost.ts` reads
`https://ollama-pricing.<domain>/v1/opencode` at startup and applies, through
`ctx.model.transform`:

- `cost`, USD per million tokens, so a session reports what it spent
- the display name with ollama.com's `$` … `$$$$` usage tier

Only those two fields are set, so the model list stays discovery-driven, and
the transform is replayed on every catalog rebuild, so a discovery refresh
cannot drop them. The plugin reloads once a day and does nothing when the
service is unreachable. Set `system_opencode_ollama_pricing: false` to remove it.

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

The URL and bearer secret (1Password `App - AgentMemory` › `secret`) go in
`~/.config/opencode-secrets/agentmemory.env` (mode 0600), which the wrapper exports. A
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
- `system_opencode_model`: default model, `provider/model`. Set to `ollama/deepseek-v4.1-flash:cloud` in defaults; empty leaves the choice to opencode

## Platforms

- Ubuntu/Debian
- macOS

## gateway

Registers the gateway MCP server (`https://gateway.<domain>/mcp`: email, calendar, notes, bookmarks, reminders) as a `remote` server in `opencode.jsonc`.

- opencode has its own client token, 1Password `App - Gateway` › `mcp token opencode`, listed as `opencode` in `composition_gateway_server_auth_clients`. It can be revoked without touching Claude's or Jarvis's tokens. Deploy `composition-gateway` after adding or rotating it.
- The config holds `Bearer {env:GATEWAY_MCP_TOKEN}`, never the value. The token is written to `~/.config/opencode-secrets/gateway.env` (mode 0600), which the wrapper sources.
- Variables: `system_opencode_gateway` (on/off), `_url`, `_token`, `_env_file`.
- As with agentmemory, running the Homebrew binary directly skips the wrapper, so the token is not set and the server fails to authenticate.

## searxng

Registers the SearXNG MCP server (`https://searchmcp.<domain>/mcp`, from `composition-mcp-searxng`) as a `remote` server, for web search. The service has a single shared bearer token (1Password `App - MCP SearXNG` › `auth token`), so unlike the gateway it cannot be revoked per client. The token goes in `~/.config/opencode-secrets/searxng.env` (mode 0600), sourced by the wrapper; the config holds `Bearer {env:SEARXNG_MCP_TOKEN}`.

Variables: `system_opencode_searxng` (on/off), `_url`, `_token`, `_env_file`.

## web search

opencode's own `websearch` tool — the built-in one, not the SearXNG MCP server. It is separate from SearXNG and has a fixed provider list (Exa, Firecrawl, Parallel, Tavily, TinyFish, plus the Console-hosted one), all of which cost per search. There is no way to point it at a self-hosted endpoint.

`system_opencode_websearch` is written straight to the `websearch` key:

- `false` (default) — writes `"websearch": false`, which removes the tool. SearXNG is then the only search: nothing to pay for, and no provider for the agent to fall back to when SearXNG is up.
- A provider id (`tavily`, `exa`, `parallel`, `firecrawl`, `tinyfish`, `random`) — keeps the tool and pins that provider, read from the provider's own `*_API_KEY` or connected with `/connect`.
- `""` — omits the key, leaving provider selection to the first-use prompt.

## ha-mcp

Registers Home Assistant's MCP server (`composition-ha-mcp` on homebrain, `https://ha-mcp.<domain>/<secret path>`) as a `remote` server named `homeassistant`. The endpoint has no auth beyond its secret path (`vault_composition_ha_mcp_secret_path`), so the full URL goes in `~/.config/opencode-secrets/ha-mcp.env` (mode 0600), sourced by the wrapper; the config holds `{env:HA_MCP_URL}`. Rotating the path means redeploying both roles.

Variables: `system_opencode_ha_mcp` (on/off), `_url`, `_env_file`.

## github (push + gh via a GitHub App)

Lets the agent push to the awfulwoman repos and drive `gh` without ever
reading a long-lived credential. A GitHub App installation token (1 hour) is
minted on demand; git and gh use it, and the App's private key is denied to the
sandbox.

- `~/.config/opencode-secrets/github-app.pem` holds the App private key (mode
  0600, from 1Password `External - GitHub` › `app private key`). It lives *outside* every sandbox
  allow path (a sibling of `~/.config/opencode`), so the agent cannot read it
  by default — nono cannot deny a file inside an allowed directory.
- `mint-github-token.sh` signs a JWT with that key and POSTs to
  `api.github.com` for an installation token. The wrapper runs it (outside the
  sandbox) and writes the result to `~/.config/opencode/gh-token` (mode 0600).
- The token file, not `GH_TOKEN`, is what readers use. A running session cannot
  have its environment updated, so exporting a token once would leave every
  child holding a value that dies after an hour. Instead the wrapper starts a
  background refresher that re-mints before then (45 minutes, leaving margin),
  and it exits when the session does: it watches the wrapper's own PID, which
  `exec` keeps as the sandboxed process, and checks the process start time and
  command name so a recycled PID cannot keep it alive. Nothing is minted while
  no session runs; the file's last token expires on its own within the hour and
  is left in place rather than deleted, so a running playbook cannot break a
  live session.
  The credential helper reads the file for pushes; `GH_TOKEN` is only the
  starting value for anything that reads the environment once.
- The `gh` shim is why `gh` also keeps working: `gh` takes its token from
  `GH_TOKEN` and has no file option, so the wrapper prepends
  `~/.config/opencode/bin` to `PATH` for the session. The shim re-reads the
  token file on every invocation, and passes straight through when
  `OPENCODE_GITHUB_TOKEN_FILE` is unset, so the user's own `gh` is unaffected.
- `gh` reads its config from `~/.config/gh`, but that directory is not in the
  sandbox allow-list (its `hosts.yml` holds the long-lived OAuth token). The
  wrapper instead sets `GH_CONFIG_DIR` to `~/.config/opencode/gh` (r+w in the
  sandbox), so `gh` creates a minimal config there and authenticates with
  the token alone, never touching the user's `~/.config/gh`.
- Git is pointed at HTTPS via `url.*.insteadOf` in the wrapper, so the agent
  pushes over HTTPS with `x-access-token` + the minted token; the SSH remotes
  are left untouched for manual use.
- The App needs `Contents: read/write` (git) and `Issues: read/write` (`gh`),
  installed on the repos it should reach.

To enable (once the App exists):

1. Create a GitHub App owned by the account, install it on the repos, note its
   App ID and installation ID.
2. `ansible-vault`-encrypt the App's private key as
   1Password `External - GitHub` › `app private key`, and the IDs as 1Password `External - GitHub` › `app id` and
   1Password `External - GitHub` › `app installation id` (all in `vault_external_github.yaml`).
3. Set `system_opencode_github: true`.

Variables: `system_opencode_github` (on/off, default off), `_app_id`,
`_installation_id`, `_app_key_file`, `_mint_helper`, `_credential_helper`,
`_token_file`, `_token_refresh_seconds`, `_shim_dir`, `_gh_binary`.

## Remote server (opencode serve)

`system_opencode_serve: true` runs `opencode serve` as a systemd service
(`opencode-serve`) for remote clients such as the OpenCode Mobile app. In
opencode v2 the server owns tool execution, so the wrapper runs `serve` inside
nono (`--profile`, `--allow-cwd`, `--listen-port`) and every tool call the
agent makes inherits the sandbox. Without the flag, the wrapper still runs
`serve` unsandboxed.

- Binds to `system_opencode_serve_host` (the Tailscale address) on
  `system_opencode_serve_port`. The web UI, `/doc` and `/openapi.json` answer
  without credentials; `/api/*` needs HTTP Basic, username `opencode`.
- The password is `vault_opencode_serve_password` (encrypted in `vars/main.yaml`), written to
  `~/.config/opencode-secrets/serve.env` (0600) and passed to the server via
  `OPENCODE_SERVER_PASSWORD`. The sandbox cannot read the file, but the server
  process, and so its agent, can see the variable.
- One server is one sandbox: it grants the profile's paths plus
  `system_opencode_serve_workdir`. Repos outside them are denied.
- Per-repo `opencode.json`, `AGENTS.md` and plugins are disabled by the nono
  pack. Terminals (persistent PTY) were not verified to stay inside the sandbox.

To enable, set `system_opencode_serve: true` in the host's vars. To rotate the
password, replace the value in `vars/main.yaml`:

```bash
openssl rand -hex 32 | tr -d '\n' | ansible-vault encrypt_string --stdin-name vault_opencode_serve_password
```
