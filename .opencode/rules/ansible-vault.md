# Ansible Vault

When instructing the user to encrypt a secret with `ansible-vault encrypt_string`, always embed a secret-generation command inline rather than using a placeholder. Use `openssl rand -hex 32` for passwords and encryption keys:

```bash
ansible-vault encrypt_string "$(openssl rand -hex 32)" --name 'vault_example_key'
```
