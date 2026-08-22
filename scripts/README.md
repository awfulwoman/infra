# Scripts

This directory holds scripts for infrastructure tasks.

## Ansible playbooks and roles

* [Run all core playbooks](run-core.sh) — runs every host's core playbook in sequence. It updates Galaxy dependencies first.
* [Fix playbook tags](fix-playbook-tags.py) — adds missing type and role-name tags to custom roles in every playbook.
* [Refactor compositions to composition-common](refactor-compositions.py) — converts composition-* roles to use the composition-common dependency.
* [Convert playbooks to direct composition roles](update-playbooks-compositions.py) — replaces the compositions role with individual composition-* role entries.

## Prepare a machine for Ansible

These two scripts prepare a machine for Ansible control, especially for ansible-pull.

* [Ubuntu](ansible-pull/bootstrap-ansible-ubuntu-server.sh)
* [Mac](ansible-pull/bootstrap-ansible-mac.sh)

## DNS

* [Flush DNS cache on Mac](flush-dns-macos.sh) — flushes the macOS DNS cache, and cycles Tailscale to clear its cache too.
* [Flush DNS cache on Ubuntu](flush-dns-ubuntu.sh) — restarts systemd-resolved to flush the DNS cache. Run with sudo.
* [Snapshot domain resolution + TLS state](snapshot-domains.sh) — captures, per registered service name and from both a LAN and remote (public01) vantage, the CNAME chain, resolved IP, HTTPS status, and served cert subject/issuer/expiry. See [docs/snapshots/README.md](../docs/snapshots/README.md).
* [Validate derived DNS records](validate-dns-records.sh) — fails fast, naming the composition and both hosts, if two hosts would claim the same DNS label. Runs entirely on localhost (no SSH); wired into pre-commit on any `inventory/` or `plugins/filters/dns_records.py` change.

## Logs

* [Query Logtide](logtide.py) — reads log records from the Logtide API, resolving the API key and infra domain from Vault at run time. `--level` and `--service` filter server-side; `--grep`, `--since` and `--host` filter locally, because the API accepts but ignores its own `search` and time-range parameters. Also has `stats` and `services` subcommands.

## Docker

* [Check image healthcheck tools](check-image-healthcheck-tools.sh) — reports the OS and the available healthcheck tools for a Docker image.

## Secrets

* [Generate a Laravel app key](generate-laravel-key.sh) — generates a Laravel APP_KEY in the format `base64:<32 random bytes>`.
* [Write a password to 1Password](op-infra-write.py) — generates a password and stores it in the 1Password Infra vault, through Connect.

## Backups

* [Suspend backups](suspend-backups.sh) — publishes a suspend message to server-8gb-backups over MQTT.

## Firmware

* [Update Sonoff Zigbee stick](update_zigbee_sonoff.sh)
