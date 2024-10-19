# There’s no place like 127.0.0.1

<img align="right" width="300" src="https://i.insider.com/5b8ec9f52badb96daa2c4818?width=700" alt="">

Let me show you my home network setup. 

![Storage](https://healthchecks.io/badge/37a7ad4c-57bd-4cea-9118-f2c5df/1bQ__A5n/host-storage.svg)


- **Configuration as code:** `true`
- **Networking:** internal DHCP and DNS via an OPNsense box. WireGuard VPN via Tailscale. 
- **Hardware management:** all machines controlled via [Ansible](ansible).
- **Networking:** provisioned via Terraform.

I started out writing this as a series of notes but it's growing into a mini-opera composed of weird sentence structures and addressing a constantly switching audience. I shall one day address this issue.

The majority of this repo is configuration code. But in `docs` there's a lot about the hardware and the reasons for my decisions. [View the docs directly in this repo](docs/) or [view the docs via a rendered site](https://awfulwoman.github.io/infra/).


# Installation

```
# Clone repo
git clone git@github.com:awfulwoman/home.git /opt/ansible/home/

# Bootstrap Ubuntu
/opt/ansible/home/scripts/bootstrap-ubuntu.sh

# Run Ansible
/opt/ansible/ansible-pull-full.sh
```
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

UPDATE 1 YEAR LATER: I became a manager again. But it's MUCH better this time. ❤️

</details>


