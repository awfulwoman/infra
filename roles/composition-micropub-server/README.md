# composition-micropub-server

[micropub-server](https://github.com/awfulwoman/micropub-server): our Python Micropub and
IndieAuth server. Publishes posts to awfulwoman.com by committing Hugo Markdown to
`awfulwoman/awfulwoman.com` on `main`. Replaces `composition-indiekit`.

Endpoint: `https://indie.<personal domain>` (public; CNAME in infra-public-resources).
Cut-over steps: `docs/deploy/README.md` in the micropub-server repo.

| Variable | Purpose |
| --- | --- |
| `composition_micropub_server_image` | Pinned `sha-` tag of the GHCR image. |
| `vault_composition_micropub_server_secret` | Signs sessions and tokens. |
| `vault_composition_micropub_server_password_secret` | bcrypt login hash. |
| `vault_composition_micropub_server_github_token` | PAT, Contents read/write on the site repo. |
| `vault_composition_micropub_server_mastodon_token` | Optional; enables Mastodon sharing. |

`files/site-micropub.yaml` is a fallback copy of the site's post types; the site's own
`data/micropub.yaml` takes over once committed there.

Data: `config/data` (SQLite: tokens, share queue), ZFS policy `low`. Posts live in git.
Check: `docker exec micropub-server micropub-server check`; health at `/health`.
