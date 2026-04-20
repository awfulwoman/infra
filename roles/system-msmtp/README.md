# System MSMTP

Configures [msmtp](https://marlam.de/msmtp/) as a lightweight mail transfer agent for outbound email. Installs `msmtp` and `msmtp-mta` (which provides a sendmail-compatible interface), then deploys a system-wide configuration for SMTP relay.

## Configuration

The configuration at `/etc/msmtprc` is deployed from a Jinja2 template and sets up a single account (`mbox`) using STARTTLS on port 587. Credentials are sourced from Ansible Vault variables:

| Vault Variable | Purpose |
|---|---|
| `vault_smtp_host` | SMTP relay hostname |
| `vault_smtp_user` | SMTP username / from address |
| `vault_smtp_password` | SMTP password |

## Design Notes

`msmtp-mta` installs a sendmail-compatible wrapper, meaning any tool that calls `/usr/sbin/sendmail` (e.g. cron, system mailers) will route mail through msmtp without additional configuration. TLS is enforced and the system CA bundle is used for certificate verification.

The config file is owned by the Ansible user rather than root, which allows user-level mail delivery without elevated privileges.
