## Dependencies

The Ansible Control Node needs some CLI tools before anything else can happen. 

`brew install` ...
- `ansible`
- `kubectl`
- `helm`
- `flux`

The dependencies for Ansible need to be pulled in:

```bash
ansible-galaxy install -r meta/requirements.yaml  
```

- [Hardware](hardware.md)
- [Network](network.md)
- [Operating System](operating-system.md).
- [Installing K3s](kubernetes.md).
- [Naming IoT devices](naming_iot_devices.md).
