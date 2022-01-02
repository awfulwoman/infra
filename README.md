# At Home With The GitOps

My home GitOps setup.

* Hardware inventory management: handled by Ansible 
* Pretty much everything else: handled by Flux and Kubernetes.

---

<details>
  <summary>:rotating_light: HUMAN EMOTION SECTION :rotating_light:</summary>
  
## HUMAN EMOTION: PLEASE LEAVE IF YOU ARE TOO TECHY

![](https://media.giphy.com/media/13f5iwTRuiEjjW/giphy.gif)

This is all part of a huge learning and emotional experience for me. I spent a lot of 2020 and 2021 in hospital, dealing with a lot of medica shit. When I got out my brain decided that I needed to make some changes to my life. So one of those things was to make a BIG BIG BIG career change from Frontend Development (and tbh mostly being a manager and therefore mostly a spreadsheet pilot) to infrastructure & Platform Engineering as an actual engineer and not a maanger.

Part of skilling up in this new role has been doing some stuff on the side. This is one of those things.

So if you see mistakes in this repo it's because I'm new at all this. But on the brifht side I think I'm coming into this strong: I'm massively ADHD and a junior-grade space cadet my brain tens to work well at fitting things together and thinking in terms of systems, so I think I'm pretty suited for this kind thing.

BUT ENOUGH CHAT. MORE CODE.

</details>

---

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
