# Ansible Facts

Top-level `ansible_*` fact variables (e.g. `ansible_machine`, `ansible_os_family`) are deprecated and will be removed in ansible-core 2.24.

Always access facts via the `ansible_facts` dict:

```yaml
# Bad
ansible_machine == 'arm64'

# Good
ansible_facts['machine'] == 'arm64'
```

Note the `ansible_` prefix is dropped inside the dict key.
