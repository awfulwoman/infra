# Voicepacks

Runs the service from [awfulwoman/dreame](https://github.com/awfulwoman/dreame): it generates voice packs for the Dreame L10 Pro vacuum, serves them, and installs them through Valetudo. The image `ghcr.io/awfulwoman/dreame` is built by that repo's GitHub workflow.

## Endpoint

`https://voicepacks.<domainname_infra>` (internal DNS via `composition_dns_subdomains`, TLS via Traefik).

The robot downloads packs from this URL itself (`GET /packs/<name>.tar.gz`, no auth), so it must resolve the name through its DNS server (192.168.1.1). Its `wget` accepts Let's Encrypt certificates. Generate and install are `POST`s with `Authorization: Bearer <token>`:

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" https://voicepacks.<domainname_infra>/voices/glados/install
curl https://voicepacks.<domainname_infra>/job
```

**An install deletes every other custom voice on the robot.**

## Key variables

| Variable | Default | Description |
|---|---|---|
| `composition_voicepacks_robot` | Derek's `host_ipv4` (`unmanaged-robot-derek`) | Valetudo `host[:port]`. Empty disables installs |
| `composition_voicepacks_api_token` | vault | Token for the `POST` endpoints |

## Data

`config/build` holds generated packs, `config/models` downloaded Piper models. Both are owned by uid 1000, the container user. The service regenerates missing or stale packs when it starts, so the ZFS policy is `low`.

## Deploy

`:latest` is our own image, so the role pulls on every deploy.

```bash
ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml --tags composition -e target_composition=voicepacks
```
