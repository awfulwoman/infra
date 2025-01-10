# My Home Infra

Hello, good evening, etc. Welcome to the repo where I keep alll my home infrastructure.

Yes indeed, *everything* I have on my home infra is controlled by this repo. 

Most of it is Ansible, as it's great for configuring individual machines, but you'll find some Terraform, Kubernetes, and ESPhome configs in there as well. 

Credentials are stored in this repo, but encrypted.

I access everything though Tailscale, which is an annoying dependency. But I keep the integration as light as possible so that I can detach my infra from them when they inevitably turn evil.

# Installation

Not sure why you'd want to install this, as it's my home infra. But hey, knock yourself out.

## Getting a host machine up and running

```
# Clone repo
git clone git@github.com:awfulwoman/home.git /opt/ansible/home/

# Bootstrap Ubuntu
/opt/ansible/home/scripts/bootstrap-ubuntu.sh

# Run Ansible
/opt/ansible/ansible-pull-full.sh
```
---
