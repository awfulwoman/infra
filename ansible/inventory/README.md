# Ansible Inventory

In many ways this can be considered the core of my home setup, as this is where I define all the machines that I use and what will run on them. The [Ansible Playbooks](../playbooks) depend on this section completely.

The basics of a machine name, user, and IP address are defined in [hosts.yaml], as well as the groups that each machine belongs to.

Variables are then added to [groups](group_vars) and [machines](host_vars) which can be used by the various [roles](../roles).
