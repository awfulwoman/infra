# Network

Each k8s node requires a static DHCP lease to be set on the local DHCP server. This is one of the few parts that I haven't yet automated. But I optmisticly assume there's an API for OpenWRT that will allow me to assign a MAC address to a static lease. 

I create a base domain name on the local DNS Zone. Kubernetes can then use this to create ingresses subdomains easily.
