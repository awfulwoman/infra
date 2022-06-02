# Hardware

The [Ansible Inventory](../ansible/inventory/hosts.yaml) describes everything that lives on this network.

I try to put everything into baremetal racks, because, well, it's fun, isn't it? Rip those machines out of any cases they might live in, like tortoises being ripped from their shells, and link them together on their own switch and subnet. Turn off any unnecessary gubbins. 

## Current Hardware Setup

What I've currently got on the hardware front:

- 5x Raspberry Pis running Kubernetes (K3s controlled by Flux, currently in development)
- 1x x86 desktop box running Docker (Home automation services: Home Assistant, MQTT, & Zigbee2MQTT)
- 1x Raspberry Pi running Docker (DNS via PiHole container)
- 1x Proxmox host, 32GB RAM, ZFS, 16TB raw, 8TB usable. Rackmounted.

## Desired Hardware Setup

Hardware that I'm working towards:

Physical servers (administered via Ansible):
- 1x x86 OPNsense gateway
- 1x Additional Pi as a secondary DNS.
- x86_64 board: Ubuntu baremetal, 16GB RAM, ZFS filesystem, multi-terrabyte storage - offsite data at friends apartment.
- All those Raspberry Pis put to good use. I'm thinking interactive touchscreens for Home Assistant, weather station, camera feeds, etc.

Virtual servers (administered via Terraform + Proxmox plugin):
- k3s x 5 worker nodes.
- k3s x 3 storage nodes (Longhorn).
- Docker-compose running various ad-hoc workload.
