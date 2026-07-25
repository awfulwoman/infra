# WiFi

The home network's wireless access points are **not** managed by this
repository. They're plain OpenWrt boxes, configured by hand, tracked in
`inventory/hosts-unmanaged.yaml` (`unmanaged-ap-livingroom`,
`unmanaged-ap-pantry`) with only `host_ipv4` set — no `host_mac`, no Ansible
role, no config management. Diagnosing anything wireless means SSHing into
the AP itself.

## Living room coverage is split across two physical APs, by band

| Inventory name        | IP              | Hostname                | Band    | SSID                                    | Notes |
|------------------------|-----------------|--------------------------|---------|-------------------------------------------|-------|
| `unmanaged-ap-livingroom` | `192.168.1.140` | `accesspoint-livingroom` | 5 GHz   | `Affordable Potatoes`                     | OpenWrt 22.03.0, QCA9880. `radio1` (2.4 GHz) hardware is present but its AP interface is disabled (`wireless.default_radio1.disabled='1'`) — this unit does not broadcast 2.4 GHz. |
| `unmanaged-ap-pantry`     | `192.168.1.141` | *(not yet confirmed)*   | 2.4 GHz | `Affordable Potatoes 2.4Ghz` (assumed)    | Physically in the pantry, but its 2.4 GHz signal is what actually reaches the living room's ESP32 devices — `.140` in the living room itself only does 5 GHz. |

Both presumably share the passphrase configured in `.140`'s
`wireless.default_radio0.key` (not reproduced here — treat as a secret, not
committed to this doc).

## Why the band split matters

ESP32-based devices — the Home Assistant Voice PE and "Home Assistant Voice"
satellites in particular — are **2.4 GHz-only**; they have no 5 GHz radio at
all. Losing the 2.4 GHz-only AP is invisible from every other angle: the SSID
is still up, phones and laptops (dual-band) reconnect to 5 GHz without
noticing, `bertha` and the rest of the LAN look completely healthy. Only the
2.4 GHz-only devices go dark.

**Incident, 2026-07-25**: `unmanaged-ap-pantry` (`192.168.1.141`) lost power. All four voice
assistants (`Voice PE Living Room`, `Voice PE Bedroom`,
`Home Assistant Voice 096e3a`/Kitchen, and a fourth unit) went `unavailable`
in Home Assistant simultaneously and stayed that way. The failure mode was
easy to misdiagnose: `bertha`'s DHCP log showed **zero** DHCP activity from
any of the four devices' MAC addresses the entire time — not a bad lease,
not a config issue, just complete silence at layer 2 — because they weren't
associating with anything, and nothing on the router/DHCP/DNS side could
surface that. Confirmed by SSHing directly into `.140` and finding `radio1`'s
AP interface disabled; power-cycling `.141` brought all four devices back
within a minute; and rewired straight to their expected static leases (see
[router.md § DHCP](router.md#dhcp)).

**Takeaway**: if a 2.4 GHz-only IoT device is unreachable but the WiFi
network otherwise looks fine, check that the specific AP unit serving 2.4 GHz
in that area is actually powered and broadcasting — don't assume "WiFi is up"
covers both bands.
