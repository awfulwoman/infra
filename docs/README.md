# Dependencies

We stand upon the shoulders of giants.

[https://whalecoiner.github.io/home/](View these docs via a Github Pages site).

## Control node tools

The Ansible Control Node needs some CLI tools before anything else can happen. Most of the time this is just my laptop, but it's moving towards a dedicated [jumphost](/ansible/playbooks/server_jumphost.yaml).

```bash
# MacOS
brew install ansible kubectl helm flux
```

## Ansible dependencies

Many roles come from Anisble Galaxy and need to be installed.

```bash
ansible-galaxy install -r meta/requirements.yaml  
```

## Terraform dependencies
```bash
cd terraform
terraform init
```

## Stuff

- [Learnings](learnings/)
- [Hardware](hardware/)
- [Network](network/)
- [Operating System](operating-system.md)
- [Installing K3s](kubernetes.md)
- [IoT devices](devices/)
