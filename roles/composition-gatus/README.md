# Gatus

[Gatus](https://github.com/TwiN/gatus) is a health dashboard: endpoints are
declared in YAML, grouped on the dashboard, with email alerts and SQLite
history. It runs on storage at `gatus.<domain>`.

It replaced `composition-peekaping`, which had no monitor grouping (a
roadmap item upstream), so hosts and services shared one flat list, and
whose ICMP checks could not be trusted (see below).

## Why config instead of an API

The endpoint list is templated from inventory, so there is no API sync to
reconcile, no API key to store, and no drift to detect: the config file is
the desired state, and a restart applies it. The role it replaced needed
several hundred lines of create/update/delete logic for the same result.

## Endpoints

All derived from the same data as DNS — each host's `compositions:` list
through the `dns_records` filter, plus `cnames_additional`:

| Group | What | Check |
|-------|------|-------|
| `hosts` | Every host in the `infra` group | TCP to `host_ipv4:22` |
| `dns` | `composition_gatus_dns_checks` | A query against the resolver, comparing the answer |
| `services` | Every derived service name | HTTPS, `[CONNECTED] == true` and `[STATUS] < 500` |
| `services` | Each host's `tcp_monitors_additional` | TCP connect — for LAN services that are not HTTP and have no cname |

**Host liveness is TCP, not ICMP.** A successful SSH connect proves the
host is reachable for Ansible, which is what actually matters here. It also
avoids trusting an ICMP implementation: the monitoring this replaced
(Peekaping) reported "Ping successful" for `192.168.1.249`, an address with
no host on it, while `ping` from the same machine and from another
container on the same Docker network showed 100% loss with an incomplete
ARP entry. Upstream:
[0xfurai/peekaping#226](https://github.com/0xfurai/peekaping/issues/226).
Neither `net.ipv4.ping_group_range` nor `cap_add: NET_RAW` changed the
false successes.

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
