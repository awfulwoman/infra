# OpenWebRX+

This role deploys [OpenWebRX+](https://github.com/luarvique/openwebrx), a web-based SDR receiver. It runs the `slechev/openwebrxplus` image. Compose settings follow the [upstream docker docs](https://github.com/0xAF/openwebrxplus-docker-builder).

The role serves the receiver at `https://openwebrx.{{ domainname_infra }}`. Anyone who can reach that URL can listen. Settings need the admin login.

## Dongle

OpenWebRX+ owns the RTL-SDR dongle, so no other program can use it at the same time. On the host, set `rtl_sdr_mode: openwebrx` for the `hardware-rtl-sdr` role. That role blacklists the kernel DVB drivers and stops `rtl_433` so the two do not fight over the dongle.

The container sees the dongle through a `/dev/bus/usb` bind mount and a `device_cgroup_rules` entry, so a replug does not need a restart.

## Variables

| Variable | Default | Purpose |
|---|---|---|
| `composition_openwebrx_admin_user` | `admin` | Admin user, created on first start only. |
| `composition_openwebrx_admin_password` | `vault_composition_openwebrx_admin_password` | Admin password, created on first start only. Changing it later does not reset an existing user. |

## Data

`{{ composition_config }}/etc` holds the OpenWebRX+ config files. `{{ composition_config }}/var` holds receiver settings and user data. After first deploy, sign in to the admin page and add the RTL-SDR as a source (the receiver will not tune until you do).

## Notes

- The image tag is pinned. Renovate opens PRs for updates.
- The image ships its own healthcheck (`/healthcheck.sh`), so the compose file does not set one.
- This image does not include the SoftMBE decoder. DMR, D-Star, YSF and NXDN need `slechev/openwebrxplus-softmbe`. SoftMBE decodes a proprietary voice codec, so check the legal position first.
- The container runs as root, which is how the upstream image works.
