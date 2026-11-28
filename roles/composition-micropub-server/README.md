# composition-micropub-server

[micropub-server](https://github.com/awfulwoman/micropub-server): our Python Micropub and
IndieAuth server. Publishes posts to awfulwoman.com by committing Hugo Markdown to
`awfulwoman/awfulwoman.com` on `main`. Replaced the Indiekit composition.

Endpoint: `https://indie.<personal domain>` (public; CNAME in infra-public-resources).
Cut-over steps: `docs/deploy/README.md` in the micropub-server repo.

| Variable | Purpose |
| --- | --- |
| `composition_micropub_server_image` | Pinned `sha-` tag of the GHCR image. |
| 1Password `App - Micropub Server` › `session secret` | Signs sessions and tokens. |
| 1Password `App - Micropub Server` › `login password hash` | bcrypt login hash. |
| 1Password `External - GitHub` › `micropub-server token` | PAT, Contents read/write on the site repo. |
| 1Password `External - GitHub` › `micropub-server webhook secret` | Optional; enables `/webhooks/github` for build tracking. Same secret as the GitHub webhook. |
| 1Password `App - GoToSocial` › `micropub-server token` | Optional; enables Mastodon sharing. |

`files/site-micropub.yaml` is a fallback copy of the site's post types; the site's own
`data/micropub.yaml` takes over once committed there.

Data: `config/data` (SQLite: tokens, share queue), ZFS policy `low`. Posts live in git.
Check: `docker exec micropub-server micropub-server check`; health at `/health`.
