# System Shoutrrr

Installs the [Shoutrrr](https://containrrr.dev/shoutrrr/) notification CLI tool via snap.

Shoutrrr is a universal notification sender supporting many services (Slack, Telegram, Gotify, ntfy, Discord, email, etc.) through a single URL-based interface. Installing it system-wide makes it available for use in cron jobs, shell scripts, and automation tasks that need to send alerts without coupling to a specific notification provider's SDK.

## Design Notes

- No variables; the role is a thin wrapper around a single snap install.
- Snap channel defaults are used — no version pinning.
