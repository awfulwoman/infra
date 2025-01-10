# My Home Infra

<img align="right" style="max-width: 380px; margin-left: 10px; margin-bottom: 10px;" src="https://i.insider.com/5b8ec9f52badb96daa2c4818?width=700" alt="">

Hello, good evening, etc. Welcome to the repo where I keep alll my home infrastructure.

Yes indeed, *everything* I have on my home infra is controlled by this repo. 

Most of it is Ansible, as it's great for configuring individual machines, but you'll find some Terraform, Kubernetes, and ESPhome configs in there as well.


# Getting a host machine up and running

```
# Clone repo
git clone git@github.com:awfulwoman/home.git /opt/ansible/home/

# Bootstrap Ubuntu
/opt/ansible/home/scripts/bootstrap-ubuntu.sh

# Run Ansible
/opt/ansible/ansible-pull-full.sh
```
---
