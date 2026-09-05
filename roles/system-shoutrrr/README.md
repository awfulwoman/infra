# System Shoutrrr

Installs the [Shoutrrr](https://containrrr.dev/shoutrrr/) notification CLI tool via snap.

Shoutrrr is a universal notification sender. It supports many services, for example Slack, Telegram, Gotify, ntfy, Discord, and email, through one URL-based interface. The role installs Shoutrrr system-wide, so cron jobs, shell scripts, and automation tasks can use it to send alerts. These tasks do not need a specific notification provider's SDK.

## Design Notes

- The role has no variables. It is a thin wrapper around a single snap install.
- The role uses the default snap channel. It does not pin a version.
