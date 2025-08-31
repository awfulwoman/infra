# Domains

Contains the configuration for the various public resources used in this infra. All the records are public info, which is why they're not encrypted. However some of the domain names themselves are things I'd like to leave behind me, which is why they're encrypted.

A couple of the infra domains are reused internally via split-horizon DNS. You can see more of that in [infra-named](../infra-named).

## Importing DO records

Get the record IDs

```bash
doctl compute domain records list example.com
```

Apply the IDs to a TF stansa
```bash
terraform import digitalocean_record.www example.com,<id from DO api>
```
