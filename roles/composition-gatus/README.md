# Gatus

[Gatus](https://github.com/TwiN/gatus) is a health dashboard: endpoints are
declared in YAML, grouped on the dashboard, with email alerts and SQLite
history. It runs on storage at `gatus.<domain>`.

Added alongside `composition-peekaping` to compare the two. Peekaping has
no monitor grouping (it is a roadmap item upstream), so hosts and services
share one flat list there.

## Why config instead of an API

The endpoint list is templated from inventory, so there is no API sync to
reconcile, no API key to store, and no drift to detect: the config file is
the desired state, and a restart applies it. `composition-peekaping` needs
several hundred lines of create/update/delete logic for the same result.

## Endpoints

All derived from the same data as DNS — each host's `compositions:` list
through the `dns_records` filter, plus `cnames_additional`:

| Group | What | Check |
|-------|------|-------|
| `hosts` | Every host in the `infra` group | TCP to `host_ipv4:22` |
| `dns` | `composition_gatus_dns_checks` | A query against the resolver, comparing the answer |
| `services` | Every derived service name | HTTPS, `[CONNECTED] == true` and `[STATUS] < 500` |

**Host liveness is TCP, not ICMP**, for the reason in
`composition-peekaping/README.md`: a successful SSH connect proves the host
is reachable for Ansible, which is what actually matters here.

**The default service condition is deliberately loose.** Plenty of services
answer 401, 403 or 404 on `/` quite legitimately — APIs, MCP servers, apps
that serve only a sub-path — so only a 5xx or a failed connection counts as
down. Services with a real health endpoint get a proper check through
`composition_gatus_service_overrides`:

```yaml
composition_gatus_service_overrides:
  connect:
    path: /health
    conditions: ["[STATUS] == 200"]
```

`zfs-api-<host>` names are checked on `/metrics` automatically.

## Alerting

Email on failure, through the provider `nullmailer` uses
(`vault_mailprovider_*`), after `composition_gatus_alert_failure_threshold`
consecutive failures, and again when resolved.

## Notes

- The image is `FROM scratch`: no shell, so the compose file declares no
  healthcheck and `docker exec` is not available for debugging. Use
  `docker logs gatus`.
- The config holds the SMTP password, so it is written `0600`.
- Changing the config restarts the container through a handler; Gatus does
  not reload on its own.
