# Home Assistant (Personal)

This role deploys a second, standalone Home Assistant instance for personal
use: calendars, todo lists, and similar dashboards. It stays separate from
[`composition-homeassistant`](../composition-homeassistant), the
home-automation hub (MQTT, Zigbee, ESPHome, Bluetooth). This instance uses
plain bridge networking (no `privileged` or `network_mode: host`), because it
does not need local hardware discovery.

## Manual setup (post-deploy)

1. Visit `https://ha-personal.{{ domainname_infra }}` and complete the HA
   onboarding wizard (create the admin account).

Previously, step 2 added a CalDAV integration pointed at Radicale to surface
Gateway's Reminders as `todo.*` entities. Radicale (`composition-radicale`)
is removed. Reminders now live behind
[`system-apple-reminders-server`](../system-apple-reminders-server), which
uses plain REST, not CalDAV, so this integration has no direct replacement.
If this instance still has that CalDAV integration configured, remove it from
**Settings → Devices & Services**. Otherwise, it shows as unavailable.

## Ports

This role uses bridge networking. HA listens on `8123` inside the container.
Traefik fronts it like any other composition.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/homeassistant` | HA configuration |

## DNS

Registers subdomain: `ha-personal`
