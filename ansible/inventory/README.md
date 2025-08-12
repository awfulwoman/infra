# Ansible - Inventory

In many ways this can be considered the core of my home setup, as this is where I define all the machines that I use and what will run on them. The [Ansible Playbooks](../playbooks) depend on this section completely.

Items in the inventory are defined in [hosts.yaml](hosts.yaml). Each inventory item then has an equivalent file in [host_vars](host_vars/) that defines variables unique to that host.

Hosts can also belong to one of several groups. These groups are defined in the [hosts.yaml](hosts.yaml) file, and, like the hosts, are extended in one of the files found in [groups](group_vars),
