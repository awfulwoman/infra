# Phanpy

[Phanpy](https://github.com/cheeaun/phanpy) is a web client for Mastodon-API servers. Here it fronts our GoToSocial instance.

## Endpoint

`https://fedi.<domainname_infra>` (internal only). Container port `8080`.

## How it is built

Upstream publishes no image. Phanpy is a static Vite app and its `PHANPY_*` settings are baked in at build time, so `files/Dockerfile` downloads the pinned release source, runs `npm run build`, and serves `dist/` from `nginxinc/nginx-unprivileged` (uid 101, not root).

The Phanpy version is the `PHANPY_VERSION` build arg in the Dockerfile. Renovate updates it through a custom regex manager in `renovate.json`; the `FROM` tags are updated by Renovate's Dockerfile manager.

## Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `composition_phanpy_client_name` | `Phanpy` | App name shown when authorising on the server |
| `composition_phanpy_default_instance` | `gts.awfulwoman.com` | Instance pre-filled on the login screen |

`PHANPY_WEBSITE` comes from the DNS label and `PHANPY_DISALLOW_ROBOTS` is always set.

## Data

None. All state (tokens, settings) is in the browser. ZFS policy `none`.

## Notes

- Text translation still calls the external `translang.phanpy.social` service.
- Healthcheck uses busybox `wget` on `127.0.0.1` (Alpine image).

## Deploy

```bash
ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml --tags composition -e target_composition=phanpy
```
