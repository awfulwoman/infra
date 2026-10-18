# composition-webmention-server

[webmention-server](https://github.com/awfulwoman/webmention-server): our Python service that
receives (and later sends) Webmentions for awfulwoman.com. Phase 1: receive only.

Endpoint: `https://webmention.<personal domain>` (public; CNAME in infra-public-resources).
The site advertises it with `<link rel="webmention">` in `baseof.html`.

| Variable | Purpose |
| --- | --- |
| `composition_webmention_server_image` | GHCR image. Tracks `latest`; pin a `sha-` tag to roll back. |
| `composition_webmention_server_site_url` / `_site_hosts` | The site that receives mentions. |
| `vault_composition_webmention_server_ip_hash_salt` | Salt for the rate-limit hashes. |

Data: `config/data` (SQLite: mentions, moderation rules, queue), ZFS policy `high`. Received
mentions cannot be fetched again if lost, because senders do not resend.

Review and moderate (until the admin UI exists):

```sh
docker exec webmention-server webmention-server mentions --status pending
docker exec webmention-server webmention-server approve <id>
docker exec webmention-server webmention-server trust example.com
```

Health: `/health` (the image's own HEALTHCHECK and a Gatus check use it).
