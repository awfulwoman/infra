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

## State

The role stores state on the machine that runs it. Only one person uses this machine, and only Ansible runs Terraform plans on it, so this is a reasonably safe setup.
