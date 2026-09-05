# FreshRSS

[FreshRSS](https://freshrss.org/) is a self-hosted RSS and Atom feed aggregator. It supports multi-user access, Fever and Google Reader compatible APIs, for mobile clients such as Reeder or NetNewsWire, and feed filtering and tagging.

## Ports

| Port | Service |
|------|---------|
| `8274` (localhost only) | FreshRSS web UI |

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}` | All FreshRSS config, extensions, and feed data |

## Integrations

- **Traefik**: Exposed at `freshrss.{{ domainname_infra }}` with Let's Encrypt TLS.

## Notes

This role uses the LinuxServer.io image (`lscr.io/linuxserver/freshrss`). The role persists the entire config directory, which holds the SQLite database, user accounts, feed subscriptions, and any installed extensions.
