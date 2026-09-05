# Composition Common

This role provides common infrastructure setup for Docker Compose compositions.

## Purpose

This role provides shared setup tasks that every `composition-*` role depends on. It does four things:

- Makes sure that the shared Docker bridge network exists.
- Creates ZFS datasets for composition data.
- Sets correct directory ownership.
- Calculates composition paths.

## Usage

Playbooks do not use this role directly. Instead, each `composition-*` role declares it as a dependency in its `meta/main.yaml`:

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

This role follows Ansible's dependency pattern. Each composition stays self-contained, while sharing common infrastructure setup. The role is idempotent, so it is safe to run multiple times as different compositions call it.
