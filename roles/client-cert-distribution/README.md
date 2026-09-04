# Client Cert Distribution

Pulls the internal wildcard cert bundle from bertha's distribution directory
over a delegated SSH read, validates it, and installs it atomically. Does not
wire the cert into any composition or Traefik config itself - that's for the
host that consumes `client_cert_distribution_install_dir` to do (see
#270/#271).

## What it does

1. Reads the candidate fullchain + private key from
   `client_cert_distribution_source_dir` on `client_cert_distribution_source_host`
   via a delegated `ansible.builtin.slurp`, and writes them to `.new` files in
   `client_cert_distribution_install_dir`.
2. Validates the candidate: not expired, and the key is a real pair for the
   certificate (compares `public_key_fingerprints.sha256` from
   `community.crypto.x509_certificate_info` /
   `community.crypto.openssl_privatekey_info`).
3. **Refuses to install** an invalid or mismatched candidate - the play fails
   before touching the currently-installed bundle, and the healthchecksio
   ping below is never reached.
4. Installs both files atomically (`ansible.builtin.copy` with `remote_src`
   always writes to a temp file in the destination directory first).
5. Pings a dedicated Healthchecks.io dead-man's switch, but only after a
   validated install actually happened.

| Variable | Default | Description |
|---|---|---|
| `client_cert_distribution_source_host` | `router-4gb-bertha` | Inventory host the bundle is read from, via delegated `slurp`. |
| `client_cert_distribution_source_dir` | `/fastpool/acme/distribution` | Directory on the source host holding the bundle. |
| `client_cert_distribution_bundle_name` | `*.{{ domainname_infra }}` | Filename stem the source host publishes the bundle under. |
| `client_cert_distribution_install_dir` | `/etc/ssl/internal-wildcard` | Where the validated `fullchain.crt` / `privkey.key` land. |
| `client_cert_distribution_healthcheck` | `true` | Set `false` to skip the Healthchecks.io ping. |
| `client_cert_distribution_healthcheck_name` | `{{ inventory_hostname }} - Internal Wildcard Cert` | Name of the check in Healthchecks.io. |

## Design notes

- The 1-day grace period on the dead-man's switch is intentionally tight
  relative to the certificate's own lifetime: `infra-certbot` renews with 60
  days of remaining validity still on the clock, so a broken pull/validate
  path alarms with weeks of lead time while the currently-installed cert is
  still perfectly valid - it does not wait until the cert is actually close
  to expiring.
- The bundle moves over SSH (a delegated `slurp` from the controller), not
  over an unauthenticated network service. Access control is therefore the
  same SSH access the controller already needs to manage the source host.
