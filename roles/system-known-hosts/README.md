# system-known-hosts

Publishes the SSH host keys of every managed host into `/etc/ssh/ssh_known_hosts` on a controller.

## Purpose

A controller must reach every host with plain `ssh` (scripts, manual use, containers). If a host key changes, a
personal `~/.ssh/known_hosts` entry blocks the connection. This role replaces trust-on-first-use with keys read from
the hosts themselves. Run it again after a rebuild or rekey.

## How it works

1. For each host in `system_known_hosts_group`, read `/etc/ssh/ssh_host_<type>_key.pub` over the Ansible connection.
2. Template one line per host into `system_known_hosts_path`. Each line lists all names: `host_name`,
   `host_name_medium`, `host_name_short`, `host_fqdn`, `ansible_host`, `host_ipv4`, `host_tailscale_ipv4`.
3. Hosts that are unreachable are left out and a warning shows.

## Configuration

```yaml
system_known_hosts_group: infra
system_known_hosts_key_types: [ed25519]
system_known_hosts_path: /etc/ssh/ssh_known_hosts
```

## Notes

- A stale entry in `~/.ssh/known_hosts` still wins on a mismatch. Remove it once with
  `ssh-keygen -R <name>`. After that, the system file is the only source.
- A container needs the file bind mounted to use it.
- A rebuild that regenerates host keys still changes them. Re-run this role afterwards.
