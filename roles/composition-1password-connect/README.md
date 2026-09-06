# 1Password Connect

[1Password Connect](https://developer.1password.com/docs/connect/) serves
secrets from 1Password vaults over a local REST API. It runs two containers:
`op-connect-api` (the API) and `op-connect-sync` (the vault syncer). They
share a SQLite database.

## Ports

The role publishes no host port. Reach the API only from other containers on
the shared Docker network (`op-connect-api:8080`), or through Traefik if the
host runs it.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/1password-credentials.json` | Connect server credentials (read-only) |
| `op-connect-data` **or** `{{ composition_config }}/data` | SQLite sync database — see below |

### Sync database location

`onepassword_connect_data_bind_mount` (default `false`) selects where the
sync database is stored:

- `false` — Docker-managed named volume `op-connect-data`. This lives under
  the Docker data-root, normally the OS disk.
- `true` — bind mount at `{{ composition_config }}/data`. The database then
  sits on the composition dataset (the ZFS pool) with the rest of the
  composition. The role creates the directory with owner `999:999`
  (`opuser` in the Connect images).

Enable the bind mount for a host only after you migrate its existing data:

```bash
cd /<compositions-dataset>/onepassword-connect
docker compose down
sudo mkdir -p config/data
sudo cp -a /var/lib/docker/volumes/onepassword-connect_op-connect-data/_data/. config/data/
sudo chown -R 999:999 config/data
# set onepassword_connect_data_bind_mount: true, then redeploy
docker volume rm onepassword-connect_op-connect-data   # after you confirm health
```

## Integrations

- **Traefik**: the compose file always carries router labels for
  `connect.{{ domainname_infra }}`. They take effect only on a host that
  runs Traefik. Set `labels: []` on the host's `compositions:` entry to
  stop a `connect` CNAME being derived for that host.

## Health

- `GET /heartbeat` returns `200` when the API process is up.
- `GET /health` reports each dependency. A freshly deployed server shows
  `sync: TOKEN_NEEDED` and `1Password: UNINITIALIZED` until a client makes
  the first request with a valid Connect token.
