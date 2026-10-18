# composition-webmention-server

[webmention-server](https://github.com/awfulwoman/webmention-server): our Python service that
receives and sends Webmentions for awfulwoman.com.

Endpoint: `https://webmention.<personal domain>` (public; CNAME in infra-public-resources).
The site advertises it with `<link rel="webmention">` in `baseof.html`.

| Variable | Purpose |
| --- | --- |
| `composition_webmention_server_image` | GHCR image. Tracks `latest`; pin a `sha-` tag to roll back. |
| `composition_webmention_server_site_url` / `_site_hosts` | The site that receives mentions. |
| `vault_composition_webmention_server_ip_hash_salt` | Salt for the rate-limit hashes. |
| `vault_composition_webmention_server_github_webhook_secret` | Optional; enables `/webhooks/github`. Same secret as the webhook on the site repo. |
| `composition_webmention_server_send_enabled` | Sending is off (`false`) until `seed` has run. |

Data: `config/data` (SQLite: mentions, moderation rules, queue), ZFS policy `high`. Received
mentions cannot be fetched again if lost, because senders do not resend.

Review and moderate (until the admin UI exists):

```sh
docker exec webmention-server webmention-server mentions --status pending
docker exec webmention-server webmention-server approve <id>
docker exec webmention-server webmention-server trust example.com
```

Health: `/health` (the image's own HEALTHCHECK and a Gatus check use it).

## Turning sending on

Sending reads the live site and tells every page a post links to. Do it in this order, so the
first pass does not send for 2,900 old posts:

```sh
docker exec webmention-server webmention-server seed                 # records links, sends nothing
docker exec webmention-server webmention-server backfill --all --dry-run | tail   # look, optional
```

Then set `composition_webmention_server_send_enabled: true` and deploy. Add the webhook on the
site repo (Workflow runs, payload `https://webmention.<personal domain>/webhooks/github`, the
secret above). A pass then runs after every successful site build, and every 6 hours.

Old posts are only sent on request: `backfill --since 2025-01-01` or `--source <url>`.
