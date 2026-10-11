# Public Resources

This role holds the configuration for the public resources used in this infrastructure. The records are public information, so they are not encrypted. Some domain names are personal, so those stay encrypted instead.

The role reuses a few infra domains internally, through split-horizon DNS. See [infra-named](../infra-named) for more detail.

## Importing DO records

Get the record IDs:

```bash
doctl compute domain records list example.com
```

Apply the IDs to a TF stanza:

```bash
terraform import digitalocean_record.www example.com,<id from DO api>
```

## Storage Boxes

`infra_publicresources_hcloud_storage_box` declares Hetzner Storage Boxes and their sub-accounts. The passwords come from Ansible Vault. The role passes them to Terraform as variables when it applies the plan, so they are not written into the rendered `.tf` files. They are in the Terraform state.

Hetzner assigns the host name and user name of each sub-account. The play prints them after it applies the plan.

A Storage Box has `prevent_destroy` and delete protection set, because replacing one destroys its contents.

## State

The role stores state on the machine that runs it. Only one person uses this machine, and only Ansible runs Terraform plans on it, so this is a reasonably safe setup.
