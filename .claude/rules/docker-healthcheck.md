# Docker Healthchecks

Do not use `wget` or `curl` in Docker Compose healthchecks unless the image is confirmed to include them (linuxserver.io images do; bare app images like `louislam/uptime-kuma` often do not).

Default to a shell TCP probe. Note: `/dev/tcp` is a bash feature — neither Alpine/BusyBox `sh` nor Debian `dash` (the default `/bin/sh` on Debian/slim images like `python:3.13-slim`) support it. Always use `bash -c`:

```yaml
healthcheck:
  test: ["CMD-SHELL", "bash -c 'echo > /dev/tcp/localhost/PORT'"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

**Exception — Alpine images:** Alpine doesn't have `bash`, so `/dev/tcp` won't work. Alpine images always include `busybox wget` — use that instead:

```yaml
healthcheck:
  test: ["CMD-SHELL", "wget -q --spider http://localhost:PORT/ || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

To detect Alpine: `docker exec <container> cat /etc/os-release | grep Alpine`. Confirmed Alpine images in this repo: `ghcr.io/kiwix/kiwix-serve`.

Using `wget`/`curl` in an image that lacks them causes the container to be permanently unhealthy from first deploy. When combined with Traefik's Let's Encrypt DNS challenge, this leaves stale `_acme-challenge` TXT records in Hetzner DNS, causing duplicate-value ACME errors on the next cert attempt.

## Recovery: stale `_acme-challenge` record

If Traefik logs show `hetzner: add RRSet records: invalid_input: duplicate value`, a stale challenge record is blocking cert issuance. **Restart Traefik** — it cleans up stale records and immediately retries:

```bash
ssh <host> 'docker restart traefik'
```

Do not attempt to delete the record manually via the Hetzner DNS API (`dns.hetzner.com/api/v1/`). Direct curl calls to that endpoint always redirect to the Hetzner console regardless of token — Traefik/LEGO handles the API differently and a restart is the reliable fix.
