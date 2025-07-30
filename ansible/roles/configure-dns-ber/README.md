# DNS server for home network

Based on BIND9. Takes in Ansible inventory data and spits out DNS zone files.

This role will:

* Gather info about machines in the Ansible inventory.
* Assign declared FQDNs to declared IP addresses.
* Discover application cnames and map them to host machines.

This setup will allow an external DHCP server to make changes via [DDNS](https://en.wikipedia.org/wiki/Dynamic_DNS).
