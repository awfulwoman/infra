# Home Assistant (Personal)

A second, standalone Home Assistant instance for personal use — calendars,
todo lists, and similar dashboards — kept separate from
[`composition-homeassistant`](../composition-homeassistant), which is the
home-automation hub (MQTT, Zigbee, ESPHome, Bluetooth). This instance runs
plain bridge networking (no `privileged`/`network_mode: host`) since it has
no need for local hardware discovery.

## Manual setup (post-deploy)

1. Visit `https://ha-personal.{{ domainname_infra }}` and complete the HA
   onboarding wizard (create the admin account).

Previously, step 2 added a CalDAV integration pointed at Radicale to surface
Gateway's Reminders as `todo.*` entities. Radicale has been removed
(`composition-radicale`); Reminders now lives behind
[`system-apple-reminders-server`](../system-apple-reminders-server), which
speaks plain REST, not CalDAV, so this integration has no direct replacement.
If this instance still has that CalDAV integration configured, remove it from
**Settings → Devices & Services** — it will otherwise show as unavailable.

## Ports

Bridge-networked; HA listens on `8123` inside the container, fronted by
Traefik like any other composition.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/homeassistant` | HA configuration |

## DNS

Registers subdomain: `ha-personal`
