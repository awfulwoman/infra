# Composition Common

Common infrastructure setup for Docker Compose compositions.

## Purpose

This role provides shared setup tasks that all `composition-*` roles depend on. It ensures:

- The shared Docker bridge network exists
- ZFS datasets are created for composition data
- Directory ownership is correct
- Composition paths are calculated

## Usage

This role is **not** used directly in playbooks. Instead, it's declared as a dependency in each `composition-*` role's `meta/main.yaml`:

```yaml
dependencies:
  - role: composition-common
    vars:
      composition_name: gitea
```

## Variables

### Required (from parent role)

- `composition_name`: Name of the composition (e.g., "gitea", "homeassistant")

### Optional (inherited from group_vars)

- `compositions_dataset`: ZFS dataset path for all compositions (default: `fastpool/compositions`)
- `default_docker_network`: Name of the shared Docker network (default: `guineanet`)

### Set by this role

- `composition_root`: Full path to composition directory (`/{{ compositions_dataset }}/{{ composition_name }}`)
- `composition_config`: Full path to composition config directory (`{{ composition_root }}/config`)

## Dependencies

- `system-docker` (declared in `meta/main.yaml`)

## What it creates

```
/{{ compositions_dataset }}/                    # Parent dataset (e.g., /fastpool/compositions/)
└── {{ composition_name }}/                     # Composition dataset (e.g., /fastpool/compositions/gitea/)
    └── config/                                 # Config directory
    └── docker-compose.yaml                     # (created by composition role)
    └── .environment_vars                       # (created by composition role)
```

## Design Philosophy

This role follows Ansible's dependency pattern, allowing each composition to be self-contained while sharing common infrastructure setup. It's idempotent and safe to run multiple times as different compositions call it.
