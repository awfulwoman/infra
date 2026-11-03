# preflight-onepassword

Stops a run early, with a clear message, when 1Password Connect cannot serve
secrets. Without it the same fault shows up halfway through a deploy as an
unrelated lookup error.

It checks, once per play and from the controller:

1. `onepassword_connect_token` is set and not empty.
2. `{{ onepassword_connect_host }}/health` answers within
   `preflight_onepassword_timeout` seconds (default 5).

Neither check reads a secret. Add it as the first role of a host's `core.yaml`,
for hosts in the `infra` group (the ones that get the Connect variables).

## Write token

Reading needs only the read token in Ansible Vault. Creating or changing
items (`playbooks/utility/provision-secrets.yaml`, `scripts/op-infra-write.py`)
needs a write token, which is **never** stored in Ansible Vault, Semaphore or
any file in this repo.

1. In 1Password, open the Connect server and add a token scoped to the Infra
   vault only, with read and write access.
2. Set it only in the shell that runs the provisioning, then close the shell:

   ```bash
   export OP_CONNECT_TOKEN_WRITE='<token>'
   ```
