# Hosts

All physical and virtual machines managed by this infrastructure.

## Baremetal — Berlin

| Host           | Description                              | IP              |
|----------------|------------------------------------------|-----------------|
| `bertha`       | Router / gateway — NAT, DHCP, DNS ([router.md](router.md)) | 192.168.1.1 |
| `minipc-8gb-homebrain`    | Home automation hub                      | 192.168.1.130   |
| `server-64gb-storage` | Central storage device      | 192.168.1.116   |
| `server-8gb-backups`  | Dedicated backup server | 192.168.1.118   |
| `malcolm`      | Mac Mini M4 16GB — Ollama / AI workloads | 192.168.1.99    |
| `pikvm`        | KVM over IP device                       | 192.168.1.111   |
| `belinda`      | Raspberry Pi 5 *(decommissioned, #300)*  | 192.168.1.117   |

## Personal Devices

| Host          | Description      | IP            |
|---------------|------------------|---------------|
| `host-mba2011`| MacBook Air 2011 | 192.168.1.27  |

## Virtual

| Host    | Description              | IP              | Provider      |
|---------|--------------------------|-----------------|---------------|
| `sites` | Public-facing services   | 188.245.37.81   | Hetzner Cloud |
| `vm-8gb-resolute` | Ubuntu 26.04 test VM, parked | 192.168.1.201 | libvirt on `server-64gb-storage` |
| `vm-8gb-noble`    | Ubuntu 24.04 baseline for the upgrade test | 192.168.1.202 | libvirt on `server-64gb-storage` |

## Devices (unmanaged)

| Host          | Description |
|---------------|-------------|
| `appletv`     | Apple TV    |
| `chromecast`  | Chromecast  |

## Dev

| Host              | Description                    |
|-------------------|--------------------------------|
| `vagrant-wrapper` | Local Vagrant dev environment  |
