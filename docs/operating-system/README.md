# Operating systems

Every machine on the cluster runs Raspberry Pi OS. I could have used any other distro, but it doesn't really matter, as all each machine will be doing is acting as a k3s node. Raspberry Pi OS at least has capabilites for handling the Pi hardware via the CLI.

## Requirements

- Ansible on the control host.
  - Ansible is fucking wonderful, isn't it?
- A public SSH key for the Ansible control host.
  - The control host is just a machine with this repo downloaded to it.


## Installation 

Each k3s machine needs to have passwordless SSH enabled. After changing the `pi` username (yes even on my internal network) I can copy over my machine's public key.
  - `ssh-copy-id <USER>@<IPADDRESS>`

I then install the requirements needed by Ansible. These are generally third-party roles that mean I barely have to write anything custom.

- `cd ansible`
- `ansible-galaxy install -r ansible/meta/requirements.yaml`

Finally I can bootstrap the machines.

- `ansible-playbook ansible/playbooks/k8s.yaml`

Most configuration comes from [the Ansible inventory](../ansible/inventory), where I define which machines do what, and what is installed on them.
