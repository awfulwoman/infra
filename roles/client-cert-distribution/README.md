# Client Cert Distribution

This role pulls the internal wildcard cert bundle from bertha's distribution
directory over a delegated SSH read, checks it, and installs it as one atomic
step. It does not wire the cert into any composition or Traefik config. The
host that consumes `client_cert_distribution_install_dir` must do that (see
#270/#271).

## What it does

1. Reads the candidate fullchain and private key from
   `client_cert_distribution_source_dir` on `client_cert_distribution_source_host`,
   through a delegated `ansible.builtin.slurp`. It writes them to `.new` files in
   `client_cert_distribution_install_dir`.
2. Checks the candidate: the certificate must not be expired, and the key must
   be a real pair for the certificate (the role compares
   `public_key_fingerprints.sha256` from
   `community.crypto.x509_certificate_info` and
   `community.crypto.openssl_privatekey_info`).
3. **Refuses to install** an invalid or mismatched candidate. The play fails
   before it touches the currently-installed bundle, and the healthchecksio
   ping below never runs.
4. Installs both files as one atomic step (`ansible.builtin.copy` with
   `remote_src` always writes to a temp file in the destination directory
   first).
5. Pings a dedicated Healthchecks.io dead-man's switch, but only after a
   validated install happens.

| Variable | Default | Description |
|---|---|---|
| `client_cert_distribution_source_host` | `router-4gb-bertha` | Inventory host the bundle is read from, via delegated `slurp`. |
| `client_cert_distribution_source_dir` | `/fastpool/acme/distribution` | Directory on the source host holding the bundle. |
| `client_cert_distribution_bundle_name` | `*.{{ domainname_infra }}` | Filename stem the source host publishes the bundle under. |
| `client_cert_distribution_install_dir` | `/etc/ssl/internal-wildcard` | Where the validated `fullchain.crt` / `privkey.key` land. |
| `client_cert_distribution_healthcheck` | `true` | Set `false` to skip the Healthchecks.io ping. |
| `client_cert_distribution_healthcheck_name` | `{{ inventory_hostname }} - Internal Wildcard Cert` | Name of the check in Healthchecks.io. |

## Design notes

- The 1-day grace period on the dead-man's switch is deliberately tight
  relative to the certificate's own lifetime. `infra-certbot` renews the
  certificate with 60 days of validity still left, so a broken pull or
  validate path alarms with weeks of lead time, while the currently-installed
  cert is still fully valid. It does not wait until the cert is close to
  expiry.
- The bundle moves over SSH, through a delegated `slurp` from the controller,
  not over an unauthenticated network service. Access control is the same SSH
  access the controller already needs to manage the source host.
