# network-tailscale-address

This role makes a host's Tailscale IPv4 address a declared property of the
inventory, rather than whatever Tailscale assigned at enrolment. Every host
sets `host_tailscale_ipv4` in its `host_vars`. This role holds the device to
that address.

Once an address is stable, other roles can reference it like any other
inventory fact. `infra-named` publishes these addresses as
`ts.<host_pfqdn>.{{ domainname_infra }}` A records. Compositions can point at
`hostvars['<host>']['host_tailscale_ipv4']`, instead of a hardcoded `100.x`
address.

## What it does

1. The role does nothing, unless `host_tailscale_ipv4` is set and
   `tailscale_address_enforce` is true.
2. Checks that the declared address sits inside Tailscale's `100.64.0.0/10`
   range.
3. Reads the host's current address with `tailscale ip -4`. An unenrolled
   host has no address, so there is nothing to re-address, and the role
   stops here.
4. If the current address already matches, the role stops. This is the
   normal path, so repeat runs cost one local command, and no API calls.
5. Otherwise, the role looks up the device in the tailnet **by its current
   address**, not by hostname, because Tailscale can add a suffix to the
   hostname. It then `POST`s the new address to
   `/api/v2/device/{deviceID}/ip`.
6. Waits for `tailscaled` to answer with the new address.

## Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `host_tailscale_ipv4` | *(unset)* | The address this host must hold. Set per host in `host_vars`. If unset, the role does nothing |
| `tailscale_address_enforce` | `true` | Master switch |
| `tailscale_api_base` | `https://api.tailscale.com/api/v2` | API root |
| `tailscale_address_verify_retries` | `12` | Attempts to wait for the new address |
| `tailscale_address_verify_delay` | `5` | Seconds between attempts |
| `tailscale_bin` | `tailscale` | Path to the Tailscale CLI. macOS needs the absolute path — see below |

## Where it runs

The roles that enrol a host onto the tailnet include this role immediately
after enrolment: `bootstrap-ubuntu-server` and `system-pikvm`.
`bootstrap-macos-server` also includes it, but that role does not enrol the
host; it only holds the address.

## macOS

Enrolment is not automated on macOS. `artis3n.tailscale.machine` dispatches
on `ansible_facts['distribution']` (`MacOSX` here). It ships task files only
for the Linux families, and fails on anything else. Its install path is apt,
yum, or pacman, and none of these apply to an app bundle. Tailscale is
installed by hand, as the standalone macOS app.

Pinning the address is separate, and works the same way as on Linux: one API
call, plus one local `tailscale ip -4`. Neither of these cares about the OS.
This role needs `tailscale_bin` set to an absolute path, because the
standalone app's CLI lives at `/usr/local/bin/tailscale` (a wrapper around
the binary inside the app bundle). Ansible's non-interactive SSH session
gets a PATH of `/usr/bin:/bin:/usr/sbin:/sbin`, which excludes that path.

> **CAUTION:** After a run, confirm the address with `tailscale ip -4` on
> the host. Getting `tailscale_bin` wrong does not fail the play: the read
> task is `failed_when: false`, so a missing CLI produces an empty
> `tailscale_current_ipv4`, the guard skips the block, and the play reports
> success while the address drifts. Meanwhile, `infra-named` keeps
> publishing the inventory value, so every name for the host resolves to an
> address that nothing holds.

## Prerequisites

The OAuth client behind `network-tailscale-token` needs **write access to
the `devices:core` scope**. This is separate from the `auth_keys` scope used
for enrolment. Without this scope, the address call fails with `403`. Add
the scope in the Tailscale Admin Console, under Settings → OAuth clients.

## Reassignment is disruptive

Changing a device's Tailscale address breaks every existing connection to
it. This is Tailscale's behavior, not a behavior of this role. Before the
first run, note two consequences:

* **A host reached over the tailnet loses its Ansible connection mid-play.**
  For most hosts here, `ansible_host` is a LAN address, so they are
  unaffected. But any host whose `ansible_host` is a MagicDNS name, for
  example `raspberry-pi4-4gb-albion`, drops the connection. Run the
  playbook again after MagicDNS catches up.
* **Clients cache the old address.** Flush DNS on anything that was talking
  to the host (`scripts/flush-dns.sh`).

Step 4 short-circuits repeat runs, so this only happens on the run that
changes an address.

## Addressing scheme

The role allocates addresses out of `100.80.0.0/16`, to mirror the LAN and
stay memorable: a host on `192.168.1.X` takes `100.80.1.X`. Hosts with no
LAN presence, such as the Hetzner VPS and remote nodes, get sequential
addresses from `100.80.2.0/24`.
