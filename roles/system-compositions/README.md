# System Compositions

Deploys every composition declared in a host's `compositions:` list. Default
DNS labels are discovered directly from each `composition-*` role's own
`defaults/main.yaml` (the `composition_dns_subdomains` var) via the
`composition_dns_subdomains` lookup plugin (`plugins/lookup/`) — not a
central registry.

## Purpose

`roles:` entries can't loop, so a data-driven list of compositions can't be
expressed as a static `- role: composition-X` line per service. This role is
the loop, wrapped as an ordinary role so it can sit at its normal position in
a host's `roles:` list — same as any other role, no `tasks:` block or
reordering needed at the playbook level.

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

`tags:` only needs the coarse, role-level tag(s) — "run every composition on
this host" (`composition`) plus any host-specific grouping tag (e.g. `zfs`,
`ollama`). It's written out explicitly rather than derived from
`compositions:` because Ansible resolves tags before per-host variables are
loaded, so an inventory var (including `compositions` itself) is undefined
at that point.

### Redeploying one composition

`-e target_composition=<name>` (or a comma-separated list) filters the loop
directly, reading straight from `compositions:`:

```bash
ansible-playbook playbooks/hosts/server-64gb-storage/core.yaml \
  --tags composition -e target_composition=jellyfin
```

An earlier version of this role's usage also carried a `composition-<name>`
tag per entry (`composition-jellyfin`, `composition-gitea`, ...), one per
host, kept in sync by hand — that's what `target_composition` replaces.
It couldn't be done the other way around (each composition declaring its own
tag, the way `composition_dns_subdomains` works) because role defaults
aren't loaded early enough for tag templating when a role is included
dynamically inside a loop, only when it's statically listed under `roles:`
— confirmed empirically, not just documented here as an assumption.
