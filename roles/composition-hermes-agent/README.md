# Hermes Agent

[Hermes Agent](https://github.com/NousResearch/hermes-agent) is a self-hosted
agent from Nous Research. It runs as a long-lived gateway process with a web
dashboard, and drives an LLM over an OpenAI-compatible API.

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

## Model

The agent talks to Ollama on Malcolm over its OpenAI-compatible endpoint
(`llm_default_openai_uri`). Hermes calls any such endpoint the "custom"
provider. `config.yaml` is the only place that carries the model, provider and
base URL — `LLM_MODEL` in `.env` was removed upstream.

**Ollama context length.** Hermes refuses to start on a context window under
64,000 tokens: the system prompt, tool schemas and working conversation state
do not fit in less. Malcolm sets `OLLAMA_CONTEXT_LENGTH: 8192`, which looks
like it collides with that, but it does not — it governs models Ollama loads
and runs itself, and Malcolm currently serves only cloud models
(`gemma4:31b-cloud`, `kimi-k3:cloud`), where Ollama proxies to Ollama Cloud and
the model's own window applies. Measured against Malcolm on 2026-09-10: a
70,045-token prompt was accepted whole, with a value planted at token 0
recalled correctly. Had the 8192 cap applied, Ollama would have truncated from
the front and lost it.

The cap does bite if Malcolm is ever given a genuinely local model and Hermes
is pointed at it. Raise `system_ollama_env.OLLAMA_CONTEXT_LENGTH` in Malcolm's
host_vars to at least 64000 before doing that, and budget the memory: Malcolm
holds up to `OLLAMA_MAX_LOADED_MODELS` models with `OLLAMA_KEEP_ALIVE: -1`.

## Dashboard

The dashboard holds the agent's API keys, so it has an auth gate that engages
on any non-loopback bind and fails closed when no auth provider is configured.
`HERMES_DASHBOARD_INSECURE` no longer bypasses it. This role uses the bundled
`basic` provider, so a username, password and cookie-signing secret are all
mandatory; `tasks/main.yaml` asserts they are present.

The container publishes no host port. Only the shared Docker network reaches
port 9119, and Traefik fronts that at `hermes.<domain>`.

## Terminal backend

`terminal.backend: local` runs the agent's shell commands inside this
container. The `docker` backend would need `/var/run/docker.sock` mounted,
which gives the agent the host — do not set it here.

## Profiles

Hermes runs an agent per *profile*. The built-in `default` profile is always
present (`data/config.yaml`) and its gateway is supervised by the image
regardless. `composition_hermes_agent_profiles` is a map of extra named profiles;
for each one the role:

1. runs `hermes profile create <name> --clone` in the container (once),
2. templates `data/profiles/<name>/config.yaml` — including that profile's own
   `mcp_servers`,
3. and, for whichever profile `composition_hermes_agent_active_profile` names,
   runs `hermes profile use <name>` so the CLI, dashboard and `hermes mcp list`
   default to it.

Each profile's gateway runs its own OpenAI-API server. The image auto-generates
an `API_SERVER_KEY` per profile (and `--clone` copies one in), so without
distinct ports the gateways clash on startup. Ports are
`composition_hermes_agent_api_server_port` (8642, the `default` profile) plus the
1-based position of each named profile in the map — so list order matters. A
profile can pin its port with an `api_server_port` key.

```yaml
composition_hermes_agent_profiles:
  nabu:
    description: "Nabu helps run the home"
    mcp_servers: {}
    disabled_tools:            # -> agent.disabled_toolsets (tool-granular)
      - browser_exec
  jarvis:
    description: "Jarvis has exclusive use of the gateway MCP"
    mcp_servers:
      gateway:
        url: "https://gateway.{{ domainname_infra }}/mcp"
        headers:
          Authorization: "Bearer ${GATEWAY_MCP_TOKEN}"
composition_hermes_agent_active_profile: jarvis
```

A profile's `disabled_tools` list is written to `agent.disabled_toolsets` in its
`config.yaml` — Hermes applies that list last, at individual-tool granularity, so
plain tool names (`browser_exec`, `browser_vault_unlock`, …) work, not just
toolset names (`browser`, `web`).

`minipc-8gb-agatha` runs `nabu` ("Nabu helps run the home", no MCP) and `jarvis`
(gateway MCP only), with `jarvis` active.

## MCP servers

Each profile's `mcp_servers` dict is written verbatim under `mcp_servers:` in
that profile's `config.yaml`. Keep bearer tokens out of `config.yaml`: put a
`${ENVVAR}` placeholder in the header and supply the value through
`composition_hermes_agent_mcp_env`, rendered into `.environment_vars` — which is
process-wide, so every profile's gateway can read it, but only profiles whose
config names a server actually connect. `config.yaml` stays a diffable,
secret-free file; `.environment_vars` is `0600` and `no_log`.

```yaml
composition_hermes_agent_mcp_env:
  GATEWAY_MCP_TOKEN: "{{ vault_gateway_mcp_token_hermes }}"
```

The [`gateway`](../composition-gateway) server gates `/mcp` on a labelled bearer
token — this profile logs as caller `hermes` in gateway's usage log.
`vault_gateway_mcp_token_hermes` lives in
`inventory/group_vars/infra/vault_gateway.yaml` alongside gateway's other client
tokens, so both this role and `composition-gateway` read the same secret; adding
it needs a `composition-gateway` re-run too (its `GATEWAY_SERVER__AUTH_TOKENS`
gains the `hermes:` entry). The unrelated `jarvis` label there belongs to the
[`composition-jarvis`](../composition-jarvis) chives bot, **not** this profile.

## Key variables

| Variable | Default | Description |
|----------|---------|-------------|
| `composition_hermes_agent_image` | `nousresearch/hermes-agent:latest` | Published image |
| `composition_hermes_agent_model` | `{{ llm_default_model }}` | Model ID passed to Ollama |
| `composition_hermes_agent_base_url` | `{{ llm_default_openai_uri }}` | Malcolm's OpenAI-compatible endpoint |
| `composition_hermes_agent_context_length` | `64000` | Hermes' floor for agent use |
| `composition_hermes_agent_terminal_backend` | `local` | Shell tool backend |
| `composition_hermes_agent_dashboard` | `true` | Run the dashboard slot |
| `composition_hermes_agent_api_server` | `false` | Expose the OpenAI-compatible API on 8642 |
| `composition_hermes_agent_manage_config` | `true` | Let Ansible own `config.yaml` |
| `composition_hermes_agent_profiles` | `{}` | Map of named profiles; each has `description`, `mcp_servers`, optional `api_server_port` |
| `composition_hermes_agent_active_profile` | `""` | Which managed profile the dashboard/CLI default to (`""`/`default` = built-in) |
| `composition_hermes_agent_api_server_port` | `8642` | Base OpenAI-API port; named profiles get base + list position |
| `composition_hermes_agent_mcp_env` | `{}` | `ENVVAR: value` pairs → `.environment_vars` (for `${ENVVAR}` in any profile's `mcp_servers`) |
| `composition_hermes_agent_dashboard_theme` / `_font` | `""` | Passed through to the profile `config.yaml` `dashboard:` block |

## Vault variables

| Variable | Required | Description |
|----------|----------|-------------|
| `vault_hermes_agent_dashboard_username` | when dashboard is on | Dashboard login |
| `vault_hermes_agent_dashboard_password` | when dashboard is on | Dashboard password |
| `vault_hermes_agent_dashboard_secret` | when dashboard is on | Signs session cookies; without it sessions die on restart |
| `vault_hermes_agent_api_server_key` | when API server is on | Bearer key for the API endpoint |
| `vault_gateway_mcp_token_hermes` | to wire the gateway MCP server | Bearer token for gateway `/mcp`; in `group_vars/infra/vault_gateway.yaml`, shared with `composition-gateway` |

Generate the secret with `openssl rand -hex 32`.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/data` | Everything Hermes keeps: `config.yaml`, `.env`, `auth.json`, `SOUL.md`, `memories/`, `skills/`, `cron/`, `sessions/`, `logs/` |

## config.yaml ownership

Ansible templates `config.yaml` on every run, so `hermes setup` and
`hermes config set` inside the container do not survive. Change the role
variables instead. To hand the file back to Hermes — to run the interactive
provider wizard, say — set `composition_hermes_agent_manage_config: false`.
Note that `hermes config set` routes API keys to `/opt/data/.env`, which
`.environment_vars` overrides.

## DNS

Registers subdomain: `hermes`

## Deploying to a host

No host runs this yet — it was built and proven on camina, then removed
because camina is the Ansible control node and a shell-capable agent does not
belong beside the vault key and the SSH keys to every host.

To adopt it somewhere, add to that host's `compositions:` and give it the two
vault secrets in `inventory/host_vars/<host>/vault_hermes_agent.yaml`:

```bash
ansible-vault encrypt_string "$(openssl rand -hex 32)" --name 'vault_hermes_agent_dashboard_password'
ansible-vault encrypt_string "$(openssl rand -hex 32)" --name 'vault_hermes_agent_dashboard_secret'
```

The host needs a Traefik (`composition-reverseproxy`) for the dashboard to be
reachable by name, and needs to resolve and reach `llm_default_host` on 11434.
After the first deploy, run `infra-named` on bertha to publish the `hermes`
CNAME.

## Removing it

Set `state: absent` on the host's `compositions:` entry and run the play. That
stops the project and deletes the data directory, the compose file and
`.environment_vars`. The ZFS dataset is deliberately left behind — destroy it
by hand once you are sure:

```bash
sudo zfs destroy -r <pool>/compositions/hermes-agent
```

Then drop the entry from `compositions:` and re-run `infra-named` on bertha to
retire the CNAME.
