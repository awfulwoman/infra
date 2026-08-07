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
    tags: [composition, composition-jellyfin, composition-gitea, ...]
```

`tags:` has to be written out explicitly, not derived from `compositions:` —
Ansible resolves tags before per-host variables are loaded, so an inventory
var (including `compositions` itself) is undefined at that point.

`composition-chives` is not compatible with this role: it has no default
`composition_name` (every other composition's matches its own name) and no
default subdomains, so it's deployed as its own explicit `- role:
composition-chives` entries instead, wherever it's used.
