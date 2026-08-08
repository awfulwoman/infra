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

### Deploying the same role more than once (`composition_name`)

A dict entry can also carry `composition_name: <name>` to give that
instance a distinct identity, different from the role's own default (which
is otherwise always the role name). This is how `composition-chives` runs
twice on the same host, once as `nabu` and once as `jarvis`:

```yaml
compositions:
  - composition: chives
    composition_name: nabu
    labels: []
  - composition: chives
    composition_name: jarvis
    labels: []
```

This only overrides identity, not arbitrary per-instance config — a role
that needs that (like chives: MCP endpoints, Telegram credentials, one set
per instance) reads it from its own `<role>_instances` dict in host_vars,
keyed by `composition_name` (see `composition-chives`'s `defaults/main.yaml`
and `composition_chives_instances` in storage's host_vars). That's a
deliberate choice, not a limitation to work around: `include_role`'s `vars:`
must be a literal YAML mapping, not a single templated expression that
evaluates to one — Ansible rejects that outright ("Vars in a IncludeRole
must be specified as a dictionary") — so there's no way to splat an
arbitrary per-item dict through the loop itself. Confirmed empirically
before settling on the host_vars-lookup approach instead.

`composition_name` is deliberately *not* defaulted to the role name inside
this role's own tasks: some roles' own `composition_name` legitimately
doesn't match their role name (`composition-mcp-openzim`: `openzim-mcp`,
`composition-1password-connect`: `onepassword-connect`), and a fallback
here would silently override those to the wrong value. So `composition_name`
is only ever set when an entry explicitly asks for it; every other entry's
role default applies completely untouched, exactly as before this existed.

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
