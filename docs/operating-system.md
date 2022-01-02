# OS configuration

## Requirements

- Ansible
  - Ansible is fucking wonderful, isn't it?
- A public SSH key for the machine you're using as an Ansible control host.
  - Which is probably just your laptop.
- `ssh-copy-id <USER>@<IPADDRESS>`

## Installation 

Ensure Ansible can log into each inventory item by copying your machine's public key over.

- `ssh-copy-id {pi,ubuntu}@IPADDRESS`

Install Ansible requirements.

- `cd ansible`
- `ansible-galaxy install -r meta/requirements.yaml`

Bootstrap the servers.

- `ansible-playbook homeautomation.yaml`
