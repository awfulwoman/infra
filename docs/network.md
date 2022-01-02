# Network

Each k8s node requires a static DHCP lease set on the local DHCP server.

A base domain name should be created on the local DNS Zone for the default Ingress route's local IP address.

A base domain name should be created on in external Zone for the clusters external IP address.

Don't bother creating a local FQDN for each node - if you get the nodes to communicate with each other via a FQDN (rather than IP address) then your local DNS queries will go thought the roof as the nodes don't do a good job caching. (No seriously, the PiHole died after a million queries were logged by it in a day).