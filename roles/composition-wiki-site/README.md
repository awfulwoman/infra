# wiki-site

Builds and serves the PersonalWiki vault as a static site with
[Quartz](https://quartz.jzhao.xyz), password-protected by Traefik basic auth.
Read-only: `composition-wiki-compiler` is the only writer of the vault this
serves.

No published image exists for Quartz — it's designed to be cloned and
customised, not installed as a package — so this role builds its own small
image (`Dockerfile.j2`) from a pinned upstream tag
(`composition_wiki_site_quartz_ref`) rather than pulling one.

Pinned to v4 (`v4.5.2`), not the newer v5: v5.0.0's fresh-clone Docker build
is broken by a currently-open upstream bug (jackyzha0/quartz#2429/#2442),
confirmed by actually building and running it, not just reading the issue
tracker.

## How it stays current

The container's entrypoint runs `quartz create` once per container
filesystem (symlinking `/data/wiki` in as Quartz's content folder, fully
non-interactively, then patching `baseUrl` with `sed` since v4's `create`
has no flag for it — see `entrypoint.sh.j2`).

It does **not** use `--watch`: v4's `--watch` never fires through a
symlinked content folder (jackyzha0/quartz#2077, closed upstream as "try
v5" — not an option here, see above). Instead, the entrypoint runs
`quartz build --serve` once (serving whatever is on disk in `public/`
from then on) and reruns plain `quartz build` on a timer
(`composition_wiki_site_rebuild_interval_seconds`) in the background —
verified by hand that a running `--serve` process really does pick up a
rebuild made while it's up, with no restart needed. `--serve` binds every
interface (Quartz's own server takes no host argument), so Traefik reaches
it by container name on port 8080.

## Endpoint

`https://wiki.{{ domainname_infra }}`, Traefik basic auth: user `wiki`,
password `vault_wiki_password`.

## Key variables

| Variable | Description |
|---|---|
| `composition_wiki_site_vault_path` | Host path of the PersonalWiki Syncthing folder — set per host |
| `composition_wiki_site_quartz_ref` | Pinned upstream git tag |
| `vault_wiki_password` / `vault_wiki_htpasswd` | Plaintext / bcrypt pair for Traefik basic auth — regenerate together |

Generate the auth secrets:

```bash
PASS="$(openssl rand -hex 16)"
htpasswd -nbB wiki "$PASS"   # -> vault_wiki_htpasswd
ansible-vault encrypt_string "$PASS" --name 'vault_wiki_password'
ansible-vault encrypt_string "$(htpasswd -nbB wiki "$PASS")" --name 'vault_wiki_htpasswd'
```

## ZFS

`policy: none` — this is pure Quartz build output. The real content is the
PersonalWiki Syncthing folder, already covered by the `syncthing` dataset's
own policy.
