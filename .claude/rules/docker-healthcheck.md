# Docker Healthchecks

Do not use `wget` or `curl` in Docker Compose healthchecks unless the image is confirmed to include them (linuxserver.io images do; bare app images like `louislam/uptime-kuma` often do not).

Default to a shell TCP probe, which works on any image with a shell:

```yaml
healthcheck:
  test: ["CMD-SHELL", "echo > /dev/tcp/localhost/PORT"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

Using `wget`/`curl` in an image that lacks them causes the container to be permanently unhealthy from first deploy. When combined with Traefik's Let's Encrypt DNS challenge, this leaves stale `_acme-challenge` TXT records in Hetzner DNS, causing duplicate-value ACME errors on the next cert attempt.
