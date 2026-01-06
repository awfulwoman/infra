# ZFS Snapshot Prompt

## Initial

You are to create an Ansible role that will configure a host to perform policy-driven ZFS snapshots on configured datasets.

Each host that uses ZFS must have a `zfs` dictionary defined. Policies for datasets are defined there, via the `importance` key. If there is no explicit policy set, assume it defaults to `none`.

For full specifications see @docs/zfs.md.

## 2026-01-06

Expand the `system-zfs-policy` Ansible role so that a user can run a Python script that reports back on the current state of a host's dataset snapshots. The report should show each dataset, and each dataset should show the policy name associated with it. For each dataset the number of hourly, daily, weekly, monthly and yearly snapshots should be shown as a table.

There should be the option of outputting to `stdout` as a table or as JSON.

The snapshots considered as part of this should only be those prefixed with `autosnap`.

The script is intended to be run on any host that has had the `system-zfs-policy` role applied to it. The script should be available to all users.

Follow the coding style and structure of the `zfs-pull-backups` and `zfs-push-backups` scripts from the `backups-zfs-server` role.

This script will be deployed to each host via Ansible, as in the `backups-zfs-server`, `system-zfs-policy` roles.
