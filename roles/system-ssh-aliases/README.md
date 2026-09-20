# system-ssh-aliases

Writes an SSH config block for every managed host into the connecting user's `~/.ssh/config`. Each block gives the
full name, the medium name and the short name as aliases (for example `raspberry-pi5-4gb-belinda`, `pi-belinda`,
`belinda`).

It uses the same markers as `playbooks/utility/list-ssh-aliases.yaml`. That playbook does the same for the machine
that runs it. This role does it on a controller, as part of the host playbook.

Pair it with `system-known-hosts`, which supplies the host keys. This role sets no host key options.

## Configuration

```yaml
system_ssh_aliases_group: infra
system_ssh_aliases_config: "{{ ansible_facts['user_dir'] }}/.ssh/config"
```
