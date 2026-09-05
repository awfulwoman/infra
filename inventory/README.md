# Ansible - Inventory

This is the core of my home setup. Here, I define every machine that I use, and what runs on it. The [Ansible Playbooks](../playbooks) depend completely on this section.

[hosts.yaml](hosts.yaml) defines the items in the inventory. Each inventory item also has a matching file in [host_vars](host_vars/), which defines variables unique to that host.

## Addresses

Each host declares two addresses in its `host_vars`:

* `host_ipv4` — where it lives on the LAN.
* `host_tailscale_ipv4` — the address it holds on the tailnet.

Neither address is only a note to self. `network-netplan` applies the first
address. [`network-tailscale-address`](../roles/network-tailscale-address/README.md)
holds the device to the second address. `infra-named` publishes both as DNS
records under `domainname_infra` (`<host_pfqdn>` and `ts.<host_pfqdn>`).

Tailscale addresses come from `100.80.0.0/16`, and mirror the LAN: a host on
`192.168.1.X` takes `100.80.1.X`. Hosts with no LAN presence get addresses in
sequence from `100.80.2.0/24`.

A host can also belong to one or more groups. [hosts.yaml](hosts.yaml) defines
these groups. Like hosts, each group can extend its variables in a file under
[group_vars](group_vars).
