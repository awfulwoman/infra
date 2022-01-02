# Home

Wotcha fucks. This is the repo for my home system: hardware provisioning via Ansible, a Kubernetes cluster, automation via Home Assistant and Node Red, and lots of jazzy words like MQTT broker, Zigbee2MQTT proxy, DDNS, VPN, etc. 

Ansible handles the baremetal inventory management and Flux provisions everything else via GitOps.

## Step 0: Setting up your Control Node

Your Control Node ("what?") depnds on having some CLI tools available.

- `ansible`
- `kubectl`
- `helm`
- `flux`

Sorry, yes. "Control Node". It's a flowery way of saying "Laptop".

Isn't tech fun?

Installing Ansible dependencies:

```
ansible-galaxy install -r meta/requirements.yaml  
```

## Step 1 - Metal: There ain't no software without hardware

See: [Hardware](docs/hardware.md)

## Step 2 - Network: Make the machines talk to each other

See: [Network](docs/network.md)

## Step 3 - OS: The brains of the operation

See: [Operating System](docs/operating-system.md).

## Step 4 - k8s: Set up a Kubernetes cluster and win a medal

See: [Installing K3s](docs/kubernetes.md).
