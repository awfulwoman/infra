# System Compositions

This role deploys every composition declared in a host's `compositions:`
list. The `composition_dns_subdomains` lookup plugin (`plugins/lookup/`)
reads default DNS labels directly from each `composition-*` role's own
`defaults/main.yaml` (the `composition_dns_subdomains` var). There is no
central registry.

## Purpose

`roles:` entries cannot loop, so a data-driven list of compositions cannot
appear as a static `- role: composition-X` line per service. This role is the
loop. It is wrapped as an ordinary role, so it sits at its normal position in
a host's `roles:` list, the same as any other role. The playbook needs no
`tasks:` block and no reordering.

Each entry in `compositions:` is either a bare composition name (use its
default DNS labels) or a dict `{composition: <name>, labels: [...]}` to
override them for that host. See `plugins/filters/dns_records.py` for how
those labels turn into DNS records.

## Usage

```yaml
roles:
  - role: system-compositions
    tags: [composition]
```

`tags:` needs only the coarse, role-level tags: `composition` (run every
composition on this host) plus any host-specific grouping tag, for example
`zfs` or `ollama`. The playbook writes these tags explicitly rather than
deriving them from `compositions:`. Ansible resolves tags before it loads
per-host variables, so an inventory variable, including `compositions`
itself, is undefined at that point.

### Redeploying one composition

`-e target_composition=<name>` (or a comma-separated list) filters the loop
directly, reading straight from `compositions:`:

```bash
ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml \
  --tags composition -e target_composition=jellyfin
```

An earlier version of this usage also carried a `composition-<name>` tag per
entry, for example `composition-jellyfin` or `composition-gitea`. Someone had
to keep one tag per host in sync by hand. `target_composition` replaces this.

The role cannot work the other way around, where each composition declares
its own tag the way `composition_dns_subdomains` does. Role defaults do not
load early enough for tag templating when a role is included dynamically
inside a loop. They load early enough only when a role is listed statically
under `roles:`. Testing confirmed this. It is not an assumption.
