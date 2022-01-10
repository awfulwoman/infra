# At Home With The GitOps

<img align="right" width="100" height="100" src="http://www.fillmurray.com/100/100">
My home GitOps setup. Configuration as Code FTW.

* Hardware inventory management: handled by [Ansible](ansible).
* Pretty much everything else: handled by [Flux](flux) and Kubernetes.

I started out writing this as a series of notes but it's growing into a mini-opera composed of weird sentence structures and addressing a constantly switching audience. I shall one day address this issue.

---

<details>
  <summary>:rotating_light: HUMAN EMOTION SECTION - DO NOT CLICK IF YOU DISLIKE FEELINGS :rotating_light:</summary>
  
## HUMAN EMOTION: PLEASE LEAVE IF YOU CAN'T COPE

This is all part of a huge learning and emotional experience for me. I spent a lot of 2020 and 2021 in hospital, dealing with a lot of medical shit. 
  
When I got out I decided that some changes were needed to my life. One of those changes was to make a gigantic (and frankly ill-planned) career change from Frontend Development - where I was mostly a manager and therefore spent my majority of time piloting spreadsheets -  right over to infrastructure & Platform Engineering as *an actual engineer and not a manager*.

Part of skilling up in this new role has been doing lots of learning on the side. 
  
This repo is one of those learnings. 
  
(Also I am coming to accept that I'm a massive nerd and that I'm allowed to play with tech shit as a hobby and that I probably have lots of internalised misogyny about a womans relationship to tech).

So if you see mistakes in this repo... well, it's because I'm new at all this. But on the bright side I think I'm coming into this strong and that things will only, as they say, get better. My enormous levels of ADHD (yes really ADHD and no not just being scatty) and me being a junior-grade space cadet means that my brain works well at fitting unrelated concepts and systems together. "Shit at the detail, fantastic at the big picture" is my elevator pitch. 

Anyway, enough of that. I'm sure you're hungry for code by now.

</details>



## Current Hardware Setup

What I've currently got.

- 5x Raspberry Pis running Kubernetes (K3s controlled by Flux, currently in development)
- 1x Intel NUC running Docker (Home Assistant, DDNS)
- 1x Raspberry Pi Zero running Mosquitto MQTT Broker
- 1x Raspberry Pi Zero running Zigbee2MQTT proxy
- 1x NAS (Proxmox), 8GB RAM, MergerFS, multi-terrabyte storage

## Desired Hardware Setup

What I'm working towards.

Physical servers (administered via Ansible):
- Pi or NUC: VPN (Wireguard) baremetal - dedicated VPN machine.
- Pi or NUC: DNS (Pihole) baremetal - dedicated DNS machine.
- x86_64 board: NAS (TrueNAS) baremetal (maybe sitting on Hypervisor), 16GB RAM, ZFS filesystem, multi-terrabyte storage - used for critical data.
- x86_64 board: NAS (TrueNAS) baremetal, 16GB RAM, ZFS filesystem, multi-terrabyte storage - used for offsite data at friends apartment.
- x86_64 board: Hypervisor (Proxmox), 64GB RAM, ZFS filesystem, multi-terrabyte storage - used for most home workloads.
- All those Raspberry Pis put to good use. I'm thinking interactive touchscreens for Home Assistant, weather station, camera feeds, etc.

Virtual servers (administered via Terraform + Proxmox plugin):
- k3s x 5 worker nodes.
- k3s x 3 storage nodes (Longhorn).
- Docker-compose running various ad-hoc workload.


## Resources
- https://perfectmediaserver.com
- https://github.com/ironicbadger/infra
- https://www.tauceti.blog/posts/kubernetes-the-not-so-hard-way-with-ansible-the-basics/
- https://unraid-guides.com/2020/12/07/dont-ever-use-cheap-pci-e-sata-expansion-cards-with-unraid/
- https://github.com/onedr0p/home-ops
- https://github.com/lisenet/kubernetes-homelab
- https://www.servethehome.com/buyers-guides/top-hardware-components-freenas-nas-servers/top-picks-freenas-hbas/
- https://www.wireguard.com
- https://github.com/kelseyhightower/kubernetes-the-hard-way
- https://github.com/kubernetes/git-sync
