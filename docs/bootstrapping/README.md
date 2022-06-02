# Bootstrapping

Almost everything that I build uses the concept of Configuration as Code. That means that any sever can be bootstrapped again using Ansible and Terraform. But to get to the point of bootstrapping you need a few tools.

## Control node tools

The Ansible Control Node needs some CLI tools before anything else can happen. 

Most of the time this Control Node is just my laptop, but I'm moving towards a dedicated [jumphost](/ansible/playbooks/server_jumphost.yaml) to launch commands from.

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
