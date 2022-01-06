## Dependencies

The Control Node (or "laptop" if you're a human) needs some CLI tools before anything else can happen. 

`brew install` ...
- `ansible`
- `kubectl`
- `helm`
- `flux`

The dependencies for Ansible need to be pulled in:

```bash
ansible-galaxy install -r meta/requirements.yaml  
```

## Hardware

See: [Hardware](docs/hardware.md)

## Network

> Make the machines talk to each other!

Details at: [Network](docs/network.md)

## The Operating System

Details at: [Operating System](docs/operating-system.md).

## Kubernetes

Details at: [Installing K3s](docs/kubernetes.md).
