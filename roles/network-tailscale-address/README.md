# network-tailscale-address

Makes a host's Tailscale IPv4 address a declared property of the inventory
rather than whatever Tailscale happened to hand out at enrolment. Every host
sets `host_tailscale_ipv4` in its `host_vars`; this role holds the device to it.

Once addresses are stable they can be referenced like any other inventory fact —
`infra-named` publishes them as `ts.<host_pfqdn>.{{ domainname_infra }}` A
records, and compositions can point at
`hostvars['<host>']['host_tailscale_ipv4']` instead of a hardcoded `100.x`.

## What it does

1. Skips entirely unless `host_tailscale_ipv4` is set and
   `tailscale_address_enforce` is true.
2. Asserts the declared address sits inside Tailscale's `100.64.0.0/10` range.
3. Reads the host's current address with `tailscale ip -4`. An unenrolled host
   has none, so there is nothing to re-address — the role stops there.
4. If the current address already matches, stops. This is the normal path, so
   repeat runs cost one local command and no API calls.
5. Otherwise looks the device up in the tailnet **by its current address** (not
   by hostname, which Tailscale may have suffixed) and `POST`s the new address
   to `/api/v2/device/{deviceID}/ip`.
6. Waits for `tailscaled` to start answering with the new address.

## Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `host_tailscale_ipv4` | *(unset)* | The address this host should hold. Set per host in `host_vars`. Unset = role does nothing |
| `tailscale_address_enforce` | `true` | Master switch |
| `tailscale_api_base` | `https://api.tailscale.com/api/v2` | API root |
| `tailscale_address_verify_retries` | `12` | Attempts to wait for the new address |
| `tailscale_address_verify_delay` | `5` | Seconds between attempts |

## Where it runs

Included by the roles that enrol a host onto the tailnet, immediately after
enrolment — `bootstrap-ubuntu-server` and `system-pikvm`. Tailscale on
`apple-macmini-m4-16gb-malcolm` is installed by hand (a Homebrew cask, not an
Ansible role), so its `host_tailscale_ipv4` is declarative only: `infra-named`
publishes it, but nothing enforces it. Set that one in the Tailscale admin
console to match, or the DNS record will point somewhere wrong.

## Prerequisites

The OAuth client behind `network-tailscale-token` needs **write access to the
`devices:core` scope**, which is separate from the `auth_keys` scope used for
enrolment. Without it the address call fails with `403`. Add it in Tailscale
Admin Console → Settings → OAuth clients.

## Reassignment is disruptive

Changing a device's Tailscale address breaks every existing connection to it —
that is Tailscale's behaviour, not this role's. Two consequences worth knowing
before the first run:

* **A host reached over the tailnet loses its Ansible connection mid-play.**
  `ansible_host` for most hosts here is a LAN address, so they are unaffected,
  but anything whose `ansible_host` is a MagicDNS name (e.g.
  `raspberry-pi4-4gb-albion`) will drop and needs the playbook re-running once
  MagicDNS has caught up.
* **Clients cache the old address.** Flush DNS on anything that was talking to
  the host (`scripts/flush-dns.sh`).

Because step 4 short-circuits, this only happens on the run that actually
changes an address.

## Addressing scheme

Addresses are allocated out of `100.80.0.0/16`, mirroring the LAN so they are
memorable: a host on `192.168.1.X` takes `100.80.1.X`. Hosts with no LAN
presence (the Hetzner VPS, remote nodes) are allocated sequentially from
`100.80.2.0/24`.
