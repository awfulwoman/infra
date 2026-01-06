# Prompts

You are to create an Ansible role that will configure a host to perform policy-driven ZFS snapshots on configured datasets.

Each host that uses ZFS must have a `zfs` dictionary defined. Policies for datasets are defined there, via the `importance` key. If there is no explicit policy set, assume it defaults to `none`.

For full specifications see @docs/zfs.md.
