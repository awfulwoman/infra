# Ansible Assert Platform

This role checks that the current Ansible platform is on an allowed list. Add it at the top of any role that supports only specific operating systems. Pass `ansible_assert_platform_supported` as a list of expected `ansible_facts['system']` values, for example `Linux` or `Darwin`. The role fails fast with a clear error, instead of doing nothing or failing partway through the run.

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

`allow_duplicates: true` is set in `meta/main.yaml`. This lets multiple roles include this role in the same play, without Ansible removing the duplicate assertions. Each calling role can pass a different `ansible_assert_platform_supported` list.
