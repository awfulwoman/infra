# Ansible - Inventory

In many ways this can be considered the core of my home setup, as this is where I define all the machines that I use and what will run on them. The [Ansible Playbooks](../playbooks) depend on this section completely.

Items in the inventory are defined in [hosts.yaml](hosts.yaml). Each inventory item then has an equivalent file in [host_vars](host_vars/) that defines variables unique to that host.

## Addresses

Each host declares two addresses in its `host_vars`:

* `host_ipv4` — where it lives on the LAN.
* `host_tailscale_ipv4` — the address it holds on the tailnet.

Neither is a note-to-self: `network-netplan` applies the first,
[`network-tailscale-address`](../roles/network-tailscale-address/README.md)
holds the device to the second, and `infra-named` publishes both as DNS records
under `domainname_infra` (`<host_pfqdn>` and `ts.<host_pfqdn>` respectively).

Tailscale addresses come out of `100.80.0.0/16` and mirror the LAN, so a host on
`192.168.1.X` takes `100.80.1.X`. Hosts with no LAN presence are allocated
sequentially from `100.80.2.0/24`.

Hosts can also belong to one of several groups. These groups are defined in the [hosts.yaml](hosts.yaml) file, and, like the hosts, are extended in one of the files found in [groups](group_vars),
