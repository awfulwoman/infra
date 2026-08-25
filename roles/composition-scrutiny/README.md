# Scrutiny

S.M.A.R.T. drive health dashboard ([AnalogJ/scrutiny](https://github.com/AnalogJ/scrutiny)).

Deploys the **omnibus** image, which bundles three parts in one container:

- the collector, which runs `smartctl` against each drive on a cron schedule
- InfluxDB 2, which stores the metric history
- the web UI/API, published through Traefik

## Access

`https://scrutiny-{{ host_name }}.{{ domainname_infra }}`

The name is host-scoped because Scrutiny reports on one machine's physical
drives — several hosts can run the role without a label collision.

## Drive discovery

`composition_scrutiny_devices` is derived from `ansible_facts['devices']` at
run time, so every whole disk the kernel sees is monitored and the list stays
correct when drives are added or removed. Partitions, loop devices, ZFS zvols
(`zd*`) and device-mapper nodes are excluded — none of them carry SMART data.

NVMe drives get two entries: the namespace block device (`/dev/nvme0n1`) and
the controller character device (`/dev/nvme0`), because `smartctl --scan`
queries the latter.

Override the pattern, or the list itself, in host_vars:

```yaml
composition_scrutiny_device_pattern: '^(sd[a-z]+)$'   # SATA/SAS only
# or pin it explicitly
composition_scrutiny_devices:
  - /dev/sda
  - /dev/sdb
```

## Privileges

`SYS_RAWIO` is needed for ATA pass-through commands, `SYS_ADMIN` for NVMe.
`/run/udev` is mounted read-only so drives are labelled by model and serial
instead of by kernel `sdX` letters, which move between boots.

## Collector schedule

Defaults to daily at midnight. The omnibus entrypoint also runs one
collection when the container starts, so the dashboard populates immediately
after deployment.

```yaml
composition_scrutiny_cron_schedule: "0 0 * * *"
```

To force a collection by hand:

```bash
ssh <host> 'docker exec scrutiny /opt/scrutiny/bin/scrutiny-collector-metrics run'
```

## Relationship to `system-smartmontools`

The two are complementary and do not conflict. `system-smartmontools` runs
`smartd` on the host and emails on failure; Scrutiny keeps the metric history
and renders the dashboard. Both read SMART data, neither writes to the drives.
