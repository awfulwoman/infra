# DNS server for home network

Based on [BIND9](https://www.isc.org/bind/) (because masochism). Ingests the Ansible inventory data and spits out [DNS zone files](https://en.wikipedia.org/wiki/Zone_file).

This role will:

* Install and configure BIND.
* Gather info about machines in the Ansible inventory.
* Assign inventory FQDNs to inventory IP addresses.
* Discover application cnames and map them to inventory FQDNs.
* Generate zone files (normal and reverse).

This setup should also allow an external DHCP server to make changes via [DDNS](https://en.wikipedia.org/wiki/Dynamic_DNS).

```bash
# Check config
named-checkconf /etc/bind/named.conf.local
# Check main zone file
named-checkzone DOMAINNAME /etc/bind/zones/db.DOMAINNAME.zone
# Check reverse zone file
named-checkzone 168.192.in-addr.arpa /etc/bind/zones/db.DOMAINNAME.reverse.zone
```

This is just personal stuff. Not for use by anyone, etc.
