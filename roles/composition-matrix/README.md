# Matrix

Deploys [continuwuity](https://continuwuity.org/) - a community-maintained
fork of Conduit/conduwuit - as a private, single-container Matrix homeserver.

This exists for one reason: giving the Hermes agent
([`composition-hermes-agent`](../composition-hermes-agent)) and its owner
somewhere to talk over Matrix. It is not a general-purpose chat server and it
does not federate.

## Why continuwuity

The three homeservers with real docs are Synapse (Python, the reference
implementation, needs Postgres), Dendrite (Go, paused by Element in 2024),
and Conduit/continuwuity (Rust, single static binary, embedded RocksDB - no
external database). For a server whose entire job is hosting a couple of
accounts and a room, continuwuity's one-container-no-Postgres shape fits the
`composition-*` pattern directly. Synapse remains the better choice if this
ever needs to grow into a real multi-user, bridge-heavy instance.

## No federation

`allow_federation` is hardcoded off. This is a one-way door in both
directions: continuwuity's own docs warn against disabling federation on a
server that has already federated, and turning it on later, once this
instance has private room history, is just as irreversible in spirit. If
federation is ever wanted, stand up a new instance rather than flipping this
one.

Because it doesn't federate, `server_name` doesn't need to be reachable by
other homeservers or covered by `.well-known` delegation - it's just the
Traefik subdomain (`matrix.{{ domainname_infra }}`), which is also the
value baked into every account's Matrix ID (`@user:matrix.<domain>`).

## No shell in the image

`scripts/check-image-healthcheck-tools.sh ghcr.io/continuwuity/continuwuity:latest`
fails outright - the image has no `sh` on `PATH` at all, so none of the
`docker-healthcheck.md` patterns (which all assume some shell) apply. There's
no `healthcheck:` block here as a result. `docker inspect` confirms the image
already exposes 8008/tcp and sets `CMD ["/sbin/conduwuit"]`, so nothing else
needed overriding either.

## Configuration

continuwuity reads its config entirely from `CONTINUWUITY_*` environment
variables (each a direct uppercase of the TOML key documented at
https://continuwuity.org/reference/config.html) - no mounted config file, so
`.environment_vars` is the single source of truth. `_config_version`-style
migration concerns don't apply here the way they do for Hermes' config.yaml;
continuwuity owns its on-disk schema itself.

## Registration

`allow_registration` is on, gated by a static `registration_token` rather
than left open. Traefik only exposes this over Tailscale, but a token is
still needed to hand out to whichever accounts get created - and if
`allow_registration` is true with no token set, continuwuity mints a random
one and only ever prints it to the container's first-boot logs, which isn't
something Ansible can read back. `tasks/main.yaml` asserts the token is set
whenever registration is left open.

**The configured token doesn't work for the very first account.** On a fresh
database continuwuity always mints its own one-time bootstrap token and
prints it to `docker logs matrix`, regardless of whether
`registration_token` is set - the log message says so explicitly
("The registration token you set in your configuration will not function
until you create an account using the token above"). Register the first
(admin) account with that logged token; `vault_matrix_registration_token`
only takes effect for accounts created after that.

The first account registered becomes the instance admin automatically
(`admins_from_room` defaults to true - they're added to `#admin:<server_name>`).
Register the owner's account first, then a second account for the Hermes
agent to use. Wiring that account into the Hermes composition (a Matrix
client/MCP tool of some kind) is a separate piece of work, not done by this
role.

## Key variables

| Variable | Default | Description |
|----------|---------|--------------|
| `composition_matrix_image` | `ghcr.io/continuwuity/continuwuity:latest` | Published image (mirrored from the canonical Forgejo registry) |
| `composition_matrix_server_name` | `matrix.{{ domainname_infra }}` | Baked into every account/room ID - fixed for the life of the instance |
| `composition_matrix_port` | `8008` | Internal port; also what Traefik load-balances to |
| `composition_matrix_log` | `info` | `CONTINUWUITY_LOG` level |
| `composition_matrix_allow_federation` | `false` | Hardcoded off - see above |
| `composition_matrix_allow_registration` | `true` | Gated by the token below |
| `composition_matrix_registration_token` | `{{ vault_matrix_registration_token }}` | Required whenever registration is open |

## Vault variables

| Variable | Required | Description |
|----------|----------|--------------|
| `vault_matrix_registration_token` | when registration is open | Static token needed to register any account |

Generate it with `openssl rand -hex 32`, per `.claude/rules/ansible-vault.md`.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/data` | continuwuity's RocksDB database - accounts, rooms, messages, media |

## DNS

Registers subdomain: `matrix`

## Deploying to a host

The host needs a Traefik (`composition-reverseproxy`) for clients to reach
it by name. Add `matrix` to that host's `compositions:` list and give it
`vault_matrix_registration_token` in
`inventory/host_vars/<host>/vault_matrix.yaml`:

```bash
ansible-vault encrypt_string "$(openssl rand -hex 32)" --name 'vault_matrix_registration_token'
```

After the first deploy, run `infra-named` on bertha to publish the `matrix`
CNAME. Then check `docker logs matrix` for the one-time bootstrap token
(see "Registration" above) and use it to register the owner's account
against `https://matrix.<domain>` with any standard Matrix client - that
account becomes the instance admin. Register the Hermes agent's account
afterwards, using `vault_matrix_registration_token` instead.

## Removing it

Set `state: absent` on the host's `compositions:` entry and run the play.
That stops the project and deletes the data directory (every account, room
and message), the compose file and `.environment_vars`. The ZFS dataset
itself is deliberately left behind - destroy it by hand once you are sure:

```bash
sudo zfs destroy -r <pool>/compositions/matrix
```

Then drop the entry from `compositions:` and re-run `infra-named` on bertha
to retire the CNAME.
