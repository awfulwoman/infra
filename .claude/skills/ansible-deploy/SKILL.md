---
name: ansible-deploy
description: Use when deploying Ansible playbooks to hosts or groups, selecting
  the right playbook file, or targeting specific roles or role types with tags.
---

- `core.yaml` (if present) is the default playbook for a host or group
- Read the `name` key of a playbook to determine relevancy to the task at hand
- Each host or group can have multiple task-specific playbooks
- Deploy all roles of a certain type using a tag based on the relevant prefix (e.g. `compositions` for composition-* roles)
- Each role has its name as a unique tag, allowing fine-grained deployment

## Execution

Check for `aw-deploy` first — it provides concurrency protection, run logging, and correct PATH for subprocesses:

```bash
command -v aw-deploy >/dev/null 2>&1
```

**If available**, use `aw-deploy run`:
```bash
aw-deploy run <playbook> [--tags <tags>] [--limit <host>] [--check]
```

**If not available**, fall back to `ansible-playbook` directly:
```bash
ansible-playbook <playbook> [--tags <tags>] [--limit <host>] [--check]
```
