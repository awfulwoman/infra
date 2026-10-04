# Guinea Pig Weights

Serves the static site from [awfulwoman/guinea-pig-weights](https://github.com/awfulwoman/guinea-pig-weights): a table and a chart of the weights from the shared sheet. The site is rebuilt daily by GitHub Actions and published to `ghcr.io/awfulwoman/guinea-pig-weights`.

## Endpoint

`https://guineapigs.<domainname_infra>` (internal DNS via `composition_dns_subdomains`, TLS via Traefik).

## Key variables

| Variable | Default | Description |
|---|---|---|
| `composition_guinea_pig_weights_image` | `ghcr.io/awfulwoman/guinea-pig-weights:latest` | Image to run. Pulled on every deploy |

## Data

The weights live in the image, not on the host. Nothing is stored in the composition dataset, so its ZFS policy is `none` (see the host's `zfs:` block).

## Deploy

```bash
ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml --tags composition -e target_composition=guinea-pig-weights
```
