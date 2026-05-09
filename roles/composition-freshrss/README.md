# FreshRSS

[FreshRSS](https://freshrss.org/) is a self-hosted RSS and Atom feed aggregator. It supports multi-user access, fever/Google Reader compatible APIs (for mobile clients like Reeder or NetNewsWire), and feed filtering/tagging.

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

Uses the LinuxServer.io image (`lscr.io/linuxserver/freshrss`). The entire config directory is persisted, which includes the SQLite database, user accounts, feed subscriptions, and any installed extensions.
