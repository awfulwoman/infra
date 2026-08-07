# Client Cert Distribution

Pulls the internal wildcard cert bundle from `server-cert-distribution` (on
bertha), validates it, and installs it atomically. Does not wire the cert into
any composition or Traefik config itself - that's for the host that consumes
`client_cert_distribution_install_dir` to do (see #270/#271).

## What it does

1. Downloads the candidate fullchain + private key to `.new` files in
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
| `client_cert_distribution_server` | bertha's `host_tailscale_ipv4` | Where to pull the bundle from. |
| `client_cert_distribution_port` | `8420` | Must match `server_cert_distribution_port`. |
| `client_cert_distribution_bundle_name` | `*.{{ domainname_infra }}` | Filename stem the server publishes the bundle under. |
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
- No signature or transport-layer authentication beyond what Tailscale itself
  provides (the server only binds to its Tailscale address) - see
  `server-cert-distribution`'s README for the layered access control this
  relies on.
