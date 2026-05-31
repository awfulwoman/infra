---
name: ansible-deploy
description: Use when deploying Ansible playbooks to hosts or groups, selecting
  the right playbook file, or targeting specific roles or role types with tags.
---

- Deploy using the `ansible-playbook` CLI tool
- `core.yaml` (if present) is the default playbook for a host or group
- Read the `name` key of a playbook to determine relevancy to the task at hand
- Each host or group can have multiple task-specific playbooks
- Deploy all of a type of role using a tag based on the relevant prefix (e.g. `compositions` for composition-* roles)
- Each role has its name as a unique tag, allowing individual deployment
