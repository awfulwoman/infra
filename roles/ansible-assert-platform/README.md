# Ansible Assert Platform

Utility role that asserts the current Ansible target platform is in a caller-supplied allowlist. Include this at the top of any role that only supports specific operating systems, passing `ansible_assert_platform_supported` as a list of expected `ansible_facts['system']` values (e.g. `Linux`, `Darwin`). Fails fast with a descriptive error rather than silently doing nothing or erroring mid-run.

## Usage

```yaml
- name: Assert platform
  ansible.builtin.include_role:
    name: ansible-assert-platform
  vars:
    ansible_assert_platform_supported:
      - Linux
```

## Variables

| Variable | Default | Description |
|---|---|---|
| `ansible_assert_platform_supported` | `["Linux"]` | List of supported `ansible_facts['system']` values |

## Design Notes

`allow_duplicates: true` is set in `meta/main.yaml` so multiple roles can include this role in the same play without Ansible deduplicating the assertions. Each calling role may pass a different `ansible_assert_platform_supported` list.
