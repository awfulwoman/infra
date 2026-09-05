# System MSMTP

This role configures [msmtp](https://marlam.de/msmtp/) as a lightweight mail
transfer agent for outbound email. It installs `msmtp` and `msmtp-mta`,
which provides a sendmail-compatible interface, then deploys a system-wide
configuration for the SMTP relay.

## Configuration

The role deploys the configuration at `/etc/msmtprc` from a Jinja2 template.
It sets up a single account (`mbox`) that uses STARTTLS on port 587.
Credentials come from Ansible Vault variables:

| Vault Variable | Purpose |
|---|---|
| `vault_smtp_host` | SMTP relay hostname |
| `vault_smtp_user` | SMTP username / from address |
| `vault_smtp_password` | SMTP password |

## Design Notes

`msmtp-mta` installs a sendmail-compatible wrapper. Any tool that calls
`/usr/sbin/sendmail`, for example cron or other system mailers, routes mail
through msmtp with no extra configuration. The role enforces TLS, and uses
the system CA bundle for certificate verification.

The Ansible user, not root, owns the config file. This allows user-level
mail delivery without elevated privileges.
