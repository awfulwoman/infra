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

**Spinning disks only.** SSDs and NVMe drives are deliberately excluded.

`composition_scrutiny_devices` is derived from `ansible_facts['devices']` at
run time, so the list stays correct when drives are added or removed. Two
filters apply:

1. `composition_scrutiny_device_pattern` matches whole-disk names, dropping
   partitions, loop devices, ZFS zvols (`zd*`) and device-mapper nodes —
   none of which carry SMART data. NVMe names are not in the pattern.
2. `rotational` (from `/sys/block/<dev>/queue/rotational`) must be `1`, which
   drops SATA SSDs.

Override the list outright in host_vars to monitor something else:

```yaml
composition_scrutiny_devices:
  - /dev/sda
  - /dev/nvme0      # also needs SYS_ADMIN adding back, see below
```

### Removing a drive from the dashboard

Scrutiny keeps a device once it has seen it, so dropping a drive from
`composition_scrutiny_devices` stops new collection but leaves the old entry
and its history on the dashboard. Deleting it is destructive and therefore
deliberately not automated — do it by hand:

```bash
# list what Scrutiny currently knows about
curl -s https://scrutiny-<host>.<domain>/api/summary \
  | jq -r '.data.summary | to_entries[] | "\(.key) \(.value.device.device_name)"'

# delete one by WWN
curl -s -X DELETE https://scrutiny-<host>.<domain>/api/device/<wwn>
```

## Privileges

`SYS_RAWIO` is needed for ATA pass-through commands. NVMe additionally needs
`SYS_ADMIN`, which is not granted because no NVMe device is passed through —
add it back if you override the device list to include one.

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
