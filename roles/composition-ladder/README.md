# Ladder

[Ladder](https://github.com/everywall/ladder) is a web proxy that bypasses paywalls by stripping tracking, injecting JavaScript, and spoofing headers for known publisher domains. It is essentially a self-hosted alternative to Outline/12ft.io.

The `ruleset.yaml` template defines per-domain rules including header spoofing (user-agent, referer, cookies) and JavaScript injections to remove paywall overlays. The current ruleset covers: NYT, Washington Post, FT, The Star, Wired, New Yorker, De Morgen, and a number of other publishers.

## Ports

Internal port `8080`, bound to `127.0.0.1:8134`. Exposed via Traefik at `ladder.<domain>`.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_root }}/ruleset.yaml` | Per-domain paywall bypass rules |

## DNS

Registers subdomain: `ladder`
