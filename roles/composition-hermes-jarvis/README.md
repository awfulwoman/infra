# Hermes Jarvis

[Hermes Agent](https://github.com/NousResearch/hermes-agent) is a self-hosted
agent from Nous Research. It runs as a long-lived gateway process with a web
dashboard, and drives an LLM over an OpenAI-compatible API.

This is the "Jarvis" persona - a single dedicated Hermes container, no Hermes
"profiles" involved. See [Why one container per bot](#why-one-container-per-bot)
below for how this came to replace the earlier `composition-hermes-agent`
multi-profile deployment.

Its sibling is [`composition-hermes-nabu`](../composition-hermes-nabu) -
same role shape, different identity/model/MCP config. Not to be confused with
[`composition-jarvis`](../composition-jarvis), an unrelated Telegram "chives"
bot that already owns the `jarvis` composition name and subdomain (same
collision on the `nabu` side, with [`composition-nabu`](../composition-nabu) -
that's how these two ended up as `hermes-nabu`/`hermes-jarvis` rather than
plain `nabu`/`jarvis`).

This role deploys the published multi-arch image
(`nousresearch/hermes-agent`) rather than building from source. Upstream's
`docker-compose.yml` uses `build: .`, `network_mode: host` and a `~/.hermes`
bind mount; none of that fits this repo, so the compose file here is a
rewrite against the same image:

| Upstream | Here | Why |
|----------|------|-----|
| `build: .` | `image: nousresearch/hermes-agent` | No source checkout on the host |
| `network_mode: host` | `{{ default_docker_network }}` | Traefik routes by label |
| `~/.hermes` | `{{ composition_config }}/data` | State lands on ZFS, so snapshots cover it |
| Separate `gateway` and `dashboard` services | One container | The image supervises both under s6; `HERMES_DASHBOARD=1` starts the dashboard slot |
| Secrets in `.env` next to the compose file | `.environment_vars` from the vault | Environment variables beat `/opt/data/.env` |

## Why one container per bot

`composition-hermes-agent` originally ran `nabu` and `jarvis` as named Hermes
*profiles* inside one container, each with its own Matrix account. That
turned out not to work: every profile in a Hermes container runs as its own
OS process, but all of them are supervised by the same s6 instance and
inherit the **same container-wide environment** - `hermes gateway list`
showed `default`, `nabu` and `jarvis` as three separate PIDs, all reading the
one `.environment_vars` file. Hermes' own env-override layer
(`gateway/config_env.py`, docstring: *"env always wins over config.yaml"*)
then stamps that single shared `MATRIX_*` value over whichever profile's
`config.yaml` says otherwise - so all three profiles ended up authenticating
to Matrix as the same account, regardless of per-profile config.

This is an acknowledged, unfixed upstream bug, not a misconfiguration here:
[nousresearch/hermes-agent#66930](https://github.com/NousResearch/hermes-agent/issues/66930)
("bare profiles inherit Matrix credentials from root `~/.hermes/.env` via
`_apply_env_overrides`") and the broader
[#77464](https://github.com/NousResearch/hermes-agent/issues/77464)
("multi-profile isolation... bleed into every profile's environment") both
describe exactly this. Per-profile gateway processes are also a
**container-only** feature to begin with - `hermes_cli/service_manager.py`'s
systemd/launchd backends raise `NotImplementedError` on
`register_profile_gateway` ("container-only feature"), so bare metal doesn't
sidestep this either: it just can't run more than one profile's gateway at
once, which isn't what a "nabu and jarvis both live simultaneously" setup
needs.

The only reliable isolation boundary Docker (or any OS) actually gives is a
process's own environment - i.e. a separate container per identity. Hence
this role and its `-jarvis` sibling: same underlying image, each with its own
`.environment_vars`, own Matrix account, own subdomain, own dashboard.
Neither uses Hermes' "profiles" feature at all - each container's built-in
`default` profile *is* the bot.

## Model

The agent talks to Ollama on Malcolm over its OpenAI-compatible endpoint
(`llm_default_openai_uri`). Hermes calls any such endpoint the "custom"
provider. `config.yaml` is the only place that carries the model, provider and
base URL - `LLM_MODEL` in `.env` was removed upstream.

**Ollama context length.** Hermes refuses to start on a context window under
64,000 tokens: the system prompt, tool schemas and working conversation state
do not fit in less. Malcolm sets `OLLAMA_CONTEXT_LENGTH: 8192`, which looks
like it collides with that, but it does not - it governs models Ollama loads
and runs itself, and Malcolm currently serves only cloud models
(`gemma4:31b-cloud`, `kimi-k3:cloud`), where Ollama proxies to Ollama Cloud and
the model's own window applies.

The cap does bite if Malcolm is ever given a genuinely local model and this
bot is pointed at it. Raise `system_ollama_env.OLLAMA_CONTEXT_LENGTH` in
Malcolm's host_vars to at least 64000 before doing that.

## Dashboard

The dashboard holds the agent's API keys, so it has an auth gate that engages
on any non-loopback bind and fails closed when no auth provider is configured.
`HERMES_DASHBOARD_INSECURE` no longer bypasses it. This role uses the bundled
`basic` provider, so a username, password and cookie-signing secret are all
mandatory; `tasks/main.yaml` asserts they are present.

The container publishes no host port. Only the shared Docker network reaches
port 9119, and Traefik fronts that at `{{ composition_dns_subdomains[0] }}.<domain>`.

## Terminal backend

`terminal.backend: local` runs the agent's shell commands inside this
container. The `docker` backend would need `/var/run/docker.sock` mounted,
which gives the agent the host - do not set it here.

## Tools

`composition_hermes_jarvis_mcp_servers` is written verbatim under
`mcp_servers:` in `config.yaml`. Keep bearer tokens out of `config.yaml`: put
a `${ENVVAR}` placeholder in the header and supply the value through
`composition_hermes_jarvis_mcp_env`, rendered into `.environment_vars` (`0600`,
`no_log`).

`composition_hermes_jarvis_disabled_toolsets` is written to
`agent.disabled_toolsets`, applied last. It is **toolset**-granular only:
individual tool names are silently ignored, so to drop `browser_exec` /
`browser_vault_*` you disable the whole `browser` toolset.

## Matrix

`composition_hermes_jarvis_matrix: true` connects the gateway to a Matrix
homeserver as a chat platform - Hermes calls this out as one of 20+ platforms
it supports (Telegram, Discord, Slack, etc. among them; none of those are
wired up here).

`MATRIX_HOMESERVER`, `MATRIX_ACCESS_TOKEN` and `MATRIX_USER_ID` are
mandatory env vars - Hermes's own `required_env` for the platform lists
exactly those three, so leaving any one unset means the platform silently
never starts (no error, just nothing in the logs mentioning Matrix at all).
The access token grants full account access, so it gets the same treatment
as the dashboard secret. `MATRIX_ALLOWED_USERS` is env-only too - there is no
`config.yaml` equivalent. Only `require_mention`, `allowed_rooms` and
`free_response_rooms` are real `config.yaml` `matrix:` keys, and the latter
two are comma-separated strings, not YAML lists (Ansible vars stay lists; the
template joins them).

`MATRIX_DEVICE_ID` is worth pinning too, once you know it: without one,
Hermes gets a new device (and fresh E2EE keys) on every restart and stops
being able to decrypt history. The device ID from the account's first
`/_matrix/client/v3/login` call is the one to use.

**Getting an access token.** Register the bot's own Matrix account (against
[`composition-matrix`](../composition-matrix) if that's the homeserver in
use, with its registration token), then log in once to mint a token:

```bash
curl -s -X POST https://<homeserver>/_matrix/client/v3/login \
  -d '{"type":"m.login.password","identifier":{"type":"m.id.user","user":"jarvis"},"password":"<account password>"}'
```

The response's `access_token` is `vault_hermes_jarvis_matrix_access_token`.

## Key variables

| Variable | Default | Description |
|----------|---------|-------------|
| `composition_hermes_jarvis_image` | `nousresearch/hermes-agent:latest` | Published image |
| `composition_hermes_jarvis_model` | `{{ llm_default_model }}` | Model ID passed to Ollama |
| `composition_hermes_jarvis_base_url` | `{{ llm_default_openai_uri }}` | Malcolm's OpenAI-compatible endpoint |
| `composition_hermes_jarvis_context_length` | `64000` | Hermes' floor for agent use |
| `composition_hermes_jarvis_terminal_backend` | `local` | Shell tool backend |
| `composition_hermes_jarvis_mcp_servers` | `{}` | MCP servers for this bot |
| `composition_hermes_jarvis_disabled_toolsets` | `[]` | Toolset names to drop (`agent.disabled_toolsets`) |
| `composition_hermes_jarvis_mcp_env` | `{}` | `ENVVAR: value` pairs → `.environment_vars` (for `${ENVVAR}` in `mcp_servers`) |
| `composition_hermes_jarvis_dashboard` | `true` | Run the dashboard slot |
| `composition_hermes_jarvis_api_server` | `false` | Expose the OpenAI-compatible API on 8642 |
| `composition_hermes_jarvis_manage_config` | `true` | Let Ansible own `config.yaml` |
| `composition_hermes_jarvis_matrix` | `false` | Connect the gateway to a Matrix homeserver |
| `composition_hermes_jarvis_matrix_homeserver` | `""` | e.g. `https://matrix.ewwww.eu`; mandatory when on |
| `composition_hermes_jarvis_matrix_user_id` | `""` | e.g. `@jarvis:matrix.ewwww.eu`; mandatory when on |
| `composition_hermes_jarvis_matrix_allowed_users` | `[]` | Matrix IDs allowed to talk to the bot; env-only, no `config.yaml` equivalent |
| `composition_hermes_jarvis_matrix_device_id` | `""` | Pins E2EE device identity - see above |
| `composition_hermes_jarvis_matrix_require_mention` | `true` | Require `@mention` outside DMs |
| `composition_hermes_jarvis_matrix_allowed_rooms` / `_free_response_rooms` | `[]` | Room IDs; joined into comma-separated `config.yaml` strings |
| `composition_hermes_jarvis_dashboard_theme` / `_font` | `""` | Passed through to `config.yaml`'s `dashboard:` block |

## Vault variables

| Variable | Required | Description |
|----------|----------|--------------|
| `vault_hermes_jarvis_dashboard_username` | when dashboard is on | Dashboard login (defaults to `vault_server_username`) |
| `vault_hermes_jarvis_dashboard_password` | when dashboard is on | Dashboard password |
| `vault_hermes_jarvis_dashboard_secret` | when dashboard is on | Signs session cookies; without it sessions die on restart |
| `vault_hermes_jarvis_api_server_key` | when API server is on | Bearer key for the API endpoint |
| `vault_hermes_jarvis_matrix_access_token` | when Matrix is on | Full account access - see Matrix section above |

Generate secrets with `openssl rand -hex 32`.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/data` | Everything Hermes keeps: `config.yaml`, `.env`, `auth.json`, `SOUL.md`, `memories/`, `skills/`, `cron/`, `sessions/`, `logs/` |

## config.yaml ownership

Ansible templates `config.yaml` on every run, so `hermes setup` and
`hermes config set` inside the container do not survive. Change the role
variables instead. To hand the file back to Hermes - to run the interactive
provider wizard, say - set `composition_hermes_jarvis_manage_config: false`.
Note that `hermes config set` routes API keys to `/opt/data/.env`, which
`.environment_vars` overrides.

## DNS

Registers subdomain: `hermes-jarvis`

## Deploying to a host

The host needs a Traefik (`composition-reverseproxy`) for the dashboard to be
reachable by name, and needs to resolve and reach `llm_default_host` on
11434. After the first deploy, run `infra-named` on bertha to publish the
`hermes-jarvis` CNAME.

## Removing it

Set `state: absent` on the host's `compositions:` entry and run the play. That
stops the project and deletes the data directory, the compose file and
`.environment_vars`. The ZFS dataset is deliberately left behind - destroy it
by hand once you are sure:

```bash
sudo zfs destroy -r <pool>/compositions/hermes-jarvis
```

Then drop the entry from `compositions:` and re-run `infra-named` on bertha to
retire the CNAME.
