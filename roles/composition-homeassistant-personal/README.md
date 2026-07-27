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
2. Add the CalDAV integration to surface Gateway's Reminders as todo lists:
   **Settings → Devices & Services → Add Integration → CalDAV**
   - URL: `https://radicale.{{ domainname_infra }}/{{ radicale_username }}/`
   - Username: `{{ radicale_username }}`
   - Password: the shared Radicale password (`vault_radicale_password`)
   - Select the calendar collection(s) to import — these appear as `todo.*`
     entities.

This reuses the same Radicale account Gateway's reminders/contacts tools
already authenticate as (see [`composition-gateway`](../composition-gateway)
and [`composition-radicale`](../composition-radicale)) — no new credentials
are created.

## Ports

Bridge-networked; HA listens on `8123` inside the container, fronted by
Traefik like any other composition.

## Volumes

| Path | Purpose |
|------|---------|
| `{{ composition_config }}/homeassistant` | HA configuration |

## DNS

Registers subdomain: `ha-personal`
