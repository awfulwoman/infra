# At Home With The GitOps

** Wotcha. This is the repo for my home system: hardware provisioning via Ansible, a Kubernetes cluster, automation via Home Assistant and Node Red, and lots of jazzy words like MQTT broker, Zigbee2MQTT proxy, DDNS, VPN, Gitops, etc. **

Baremetal inventory management is handled by Ansible, and pretty much everything else via Flux.

## AWKWARD EMOTIONAL SECTION

![](https://media.giphy.com/media/13f5iwTRuiEjjW/giphy.gif)

This is all part of a huge learning experience for me. Y'see,  a few months ago I decided, on a whim, to make a BIG BIG BIG career change from Frontend Development to baby-level Platform Engineering. (It's not something I really wanted to do, but the web industry as I knew it has died and I don't feel at home there any longer).

So if you see mistakes in here it's because I'm new at this shit.

But as I'm massively ADHD and a junior-grade space cadet my brain tens to work well at fitting things together and thinking in terms of systems, so I think I'm pretty suited for all this.

ENOUGH CHAT. MORE CODE.

---

Let's break things into a few sections.

## 0 - Basic shit: The Control Node

Your Control Node ("what?") depnds on having some CLI tools available.

- `ansible`
- `kubectl`
- `helm`
- `flux`

Sorry, yes. "Control Node". It's a flowery way of saying "Laptop".

Isn't tech fun?

Installing Ansible dependencies:

```bash
ansible-galaxy install -r meta/requirements.yaml  
```

## 1 - Physical shit: The Bare Metal

See: [Hardware](docs/hardware.md)

## 2 - Talky talk shit: The Network

> Make the machines talk to each other!

Details at: [Network](docs/network.md)

## 3 - Brainy shit: The Operating System

Details at: [Operating System](docs/operating-system.md).

## 4 - Naval analogy shit: Kubernetes

Details at: [Installing K3s](docs/kubernetes.md).
