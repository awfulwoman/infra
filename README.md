# Home

This is my home system.

Runs Ansible for baremetal inventory management and Flux2 for GitOps.


Basic tools:

```
brew install ansible
brew install flux
brew install helm
```

Ansible requirements:

```
ansible-galaxy install -r meta/requirements.yaml  
```

## Installation

### Hardware

See: [Hardware](docs/hardware.md)

### Network

See: [Network](docs/network.md)

### Operating system

See: [Operating System](docs/operating-system.md).

### Activate cluster

See: [Installing K3s](docs/kubernetes.md).
