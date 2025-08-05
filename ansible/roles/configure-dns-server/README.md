# DNS server for home network

Based on BIND9. Takes in Ansible inventory data and spits out DNS zone files.

This role will:

* Gather info about machines in the Ansible inventory.
* Assign inventory FQDNs to inventory IP addresses.
* Discover application cnames and map them to inventory FQDNs.

This setup will allow an external DHCP server to make changes via [DDNS](https://en.wikipedia.org/wiki/Dynamic_DNS).

```bash
# Check config
named-checkconf /etc/bind/named.conf.local
# Check main zone file
named-checkzone DOMAINNAME /etc/bind/zones/db.DOMAINNAME.zone
# Check reverse zone file
named-checkzone 168.192.in-addr.arpa /etc/bind/zones/db.DOMAINNAME.reverse.zone
```
