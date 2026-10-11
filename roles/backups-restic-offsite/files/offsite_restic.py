#!/usr/bin/env python3
"""Send the backup server's replicas offsite with restic.

The backup server already holds a decrypted-on-demand replica of every dataset
it pulls. This reads the newest snapshot of each offsite target, read-only, and
hands it to restic. Nothing here talks to the hosts the data came from, so they
stay pull-only and never hold an offsite credential.

A target is "<client>/<dataset>", the same spelling the ZFS push role uses.

restic takes its repository and password from the environment
(RESTIC_REPOSITORY, RESTIC_PASSWORD_FILE); this script never sees either.

Standard library only: it runs as root from cron, outside any virtualenv.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

HOLD_TAG = 'offsite-restic'


# ---------------------------------------------------------------------------
# Pure logic
# ---------------------------------------------------------------------------


def split_target(target):
    """Split "<client>/<dataset>" into its two halves."""
    client, _, dataset = target.partition('/')
    return client, dataset


def replica_path(replica_root, target):
    """The local dataset holding this target's replica."""
    return f'{replica_root}/{target}'


def mount_point(mount_root, target):
    """Where this target's snapshot is mounted. Must not change between runs."""
    return f'{mount_root}/{target}'


def latest_snapshot(listing):
    """Newest snapshot from `zfs list -Hp -t snapshot -o name,creation`.

    Returns (name, creation_epoch), or None when the dataset has no snapshots.
    """
    newest = None
    for line in listing.splitlines():
        fields = line.split('\t')
        if len(fields) != 2 or not fields[0]:
            continue
        candidate = (fields[0], int(fields[1]))
        if newest is None or candidate[1] > newest[1]:
            newest = candidate
    return newest


def smallest_first(sizes):
    """Order targets by size, so the first run lands the small ones early."""
    return sorted(sizes, key=lambda target: (sizes[target], target))


def backup_command(target, mount, snapshot, created, limit_upload_kib):
    client, dataset = split_target(target)
    cmd = [
        'restic', 'backup',
        '--host', client,
        '--tag', f'dataset={dataset}',
        '--tag', f'zfs={snapshot.rpartition("@")[2]}',
        # Stamp the copy with the moment the data was frozen, not the moment
        # the upload finished, which can be days later.
        '--time', created.strftime('%Y-%m-%d %H:%M:%S'),
        '--one-file-system',
    ]
    if limit_upload_kib:
        cmd += ['--limit-upload', str(limit_upload_kib)]
    cmd.append(mount)
    return cmd


def forget_command(keep):
    cmd = ['restic', 'forget', '--group-by', 'host,paths']
    for period, count in keep.items():
        cmd += [f'--keep-{period}', str(count)]
    return cmd


def _parse_restic_time(value):
    # restic prints nanoseconds; datetime accepts at most microseconds.
    value = value.replace('Z', '+00:00')
    head, dot, tail = value.partition('.')
    if dot:
        digits = ''.join(ch for ch in tail if ch.isdigit())
        offset = tail[len(digits):]
        value = f'{head}.{digits[:6]}{offset}'
    return datetime.fromisoformat(value).timestamp()


def latest_offsite_times(repo_snapshots, mount_root):
    """Map each target to the time of its newest copy in the repository."""
    prefix = mount_root.rstrip('/') + '/'
    times = {}
    for snapshot in repo_snapshots:
        for path in snapshot.get('paths', []):
            if not path.startswith(prefix):
                continue
            target = path[len(prefix):]
            when = _parse_restic_time(snapshot['time'])
            if when > times.get(target, 0):
                times[target] = when
    return times


def needs_backup(snapshot_created, offsite_time):
    """Whether this snapshot is newer than anything already offsite."""
    return offsite_time is None or offsite_time < snapshot_created


def build_status(targets, offsite, failures, now, stale_hours, running):
    """Summarise what is offsite. Absent, late and failed are kept apart."""
    missing, stale, healthy = [], [], []
    for target in targets:
        when = offsite.get(target)
        if when is None:
            missing.append(target)
        elif now - when > stale_hours * 3600:
            stale.append(target)
        else:
            healthy.append(target)
    return {
        'ok': not (missing or stale or failures),
        'running': running,
        'checked_at': datetime.fromtimestamp(now).strftime('%Y-%m-%dT%H:%M:%S'),
        'failures': failures,
        'missing_datasets': missing,
        'stale_datasets': stale,
        'healthy_datasets': healthy,
    }


# ---------------------------------------------------------------------------
# Side effects
# ---------------------------------------------------------------------------


def log(message):
    print(f'{datetime.now():%Y-%m-%d %H:%M:%S} {message}', flush=True)


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, check=False, **kwargs)


def dataset_size(dataset):
    result = run(['zfs', 'list', '-Hp', '-o', 'used', dataset])
    return int(result.stdout.strip()) if result.returncode == 0 else None


def newest_snapshot_of(dataset):
    result = run(['zfs', 'list', '-Hp', '-t', 'snapshot', '-d', '1', '-o', 'name,creation', dataset])
    return latest_snapshot(result.stdout) if result.returncode == 0 else None


def repo_snapshots():
    result = run(['restic', 'snapshots', '--json'])
    if result.returncode != 0:
        raise RuntimeError(f'restic snapshots failed: {result.stderr.strip()}')
    return json.loads(result.stdout or '[]')


def release(snapshot, mount):
    """Unmount and unhold. Safe to call when neither is in place."""
    if os.path.ismount(mount):
        run(['umount', mount])
    run(['zfs', 'release', HOLD_TAG, snapshot])


def clear_leftovers(replica_root, mount_root):
    """Undo whatever a killed run left mounted or held."""
    with open('/proc/mounts', encoding='utf-8') as mounts:
        stale = [line.split()[1] for line in mounts if line.split()[1].startswith(mount_root + '/')]
    for mount in sorted(stale, reverse=True):
        log(f'Unmounting leftover {mount}')
        run(['umount', mount])
    held = run(['sh', '-c', f'zfs list -H -t snapshot -o name -r {replica_root} | xargs -r zfs holds -H'])
    for line in held.stdout.splitlines():
        fields = line.split('\t')
        if len(fields) >= 2 and fields[1] == HOLD_TAG:
            log(f'Releasing leftover hold on {fields[0]}')
            run(['zfs', 'release', HOLD_TAG, fields[0]])


def backup_target(target, snapshot, created, mount_root, limit_upload_kib):
    """Mount one snapshot and send it. Returns an error string, or None."""
    mount = mount_point(mount_root, target)
    os.makedirs(mount, exist_ok=True)
    # The hold keeps the replica's own retention from destroying the snapshot
    # while an upload that may take days is still reading it.
    held = run(['zfs', 'hold', HOLD_TAG, snapshot])
    if held.returncode != 0:
        return f'zfs hold failed: {held.stderr.strip()}'
    try:
        mounted = run(['mount', '-t', 'zfs', '-o', 'ro', snapshot, mount])
        if mounted.returncode != 0:
            return f'mount failed: {mounted.stderr.strip()}'
        cmd = backup_command(target, mount, snapshot, datetime.fromtimestamp(created), limit_upload_kib)
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            return f'restic backup exited {result.returncode}'
        return None
    finally:
        release(snapshot, mount)


def publish(args, status):
    if not args.mqtt_host:
        return
    safe_id = args.mqtt_name.replace('-', '_').replace('.', '_')
    topic = f'{args.mqtt_topic_prefix}/{args.mqtt_name}/offsite'
    discovery = {
        'name': f'{args.mqtt_name} Offsite Backups',
        'state_topic': topic,
        'value_template': "{{ 'ON' if not value_json.ok else 'OFF' }}",
        'payload_on': 'ON',
        'payload_off': 'OFF',
        'device_class': 'safety',
        'unique_id': f'offsite_backups_{safe_id}',
        'json_attributes_topic': topic,
        # Retained, so without an expiry a dead job keeps its last green.
        'expire_after': args.mqtt_expire_after,
    }
    messages = (
        (f'homeassistant/binary_sensor/offsite_backups_{safe_id}/config', discovery),
        (topic, status),
    )
    for message_topic, payload in messages:
        try:
            run(['mosquitto_pub', '-h', args.mqtt_host, '-t', message_topic, '-m', json.dumps(payload), '-r'], timeout=10)
        except (OSError, subprocess.SubprocessError) as exc:
            log(f'MQTT publish failed: {exc}')


def command_backup(args):
    clear_leftovers(args.replica_root, args.mount_root)

    try:
        offsite = latest_offsite_times(repo_snapshots(), args.mount_root)
    except (RuntimeError, ValueError) as exc:
        log(str(exc))
        publish(args, build_status(args.targets, {}, {'repository': str(exc)}, time.time(), args.stale_hours, False))
        return 1

    failures = {}
    sizes = {}
    for target in args.targets:
        size = dataset_size(replica_path(args.replica_root, target))
        if size is None:
            failures[target] = 'no replica on this backup server'
        else:
            sizes[target] = size

    def report(running):
        publish(args, build_status(args.targets, offsite, failures, time.time(), args.stale_hours, running))

    report(running=True)

    for target in smallest_first(sizes):
        newest = newest_snapshot_of(replica_path(args.replica_root, target))
        if newest is None:
            failures[target] = 'replica has no snapshots'
            continue
        snapshot, created = newest
        if not needs_backup(created, offsite.get(target)):
            log(f'{target}: {snapshot} is already offsite')
            continue
        log(f'{target}: sending {snapshot}')
        error = backup_target(target, snapshot, created, args.mount_root, args.limit_upload)
        if error:
            log(f'{target}: {error}')
            failures[target] = error
        else:
            offsite[target] = created
        report(running=True)

    keep = {'daily': args.keep_daily, 'weekly': args.keep_weekly, 'monthly': args.keep_monthly}
    forgot = subprocess.run(forget_command(keep), check=False, stdout=subprocess.DEVNULL)
    if forgot.returncode != 0:
        failures['forget'] = f'restic forget exited {forgot.returncode}'

    report(running=False)
    return 1 if failures else 0


def command_maintain(args):
    """prune and check share one shape: run it, and say so if it fails."""
    cmd = {
        'prune': ['restic', 'prune'],
        'check': ['restic', 'check', '--read-data-subset', args.read_data_subset],
    }[args.command]
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        log(f'restic {args.command} exited {result.returncode}')
    return result.returncode


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command', required=True)

    backup = sub.add_parser('backup', help='send the newest snapshot of every target')
    backup.add_argument('--targets', nargs='+', required=True, metavar='CLIENT/DATASET')
    backup.add_argument('--replica-root', required=True, help='local dataset the replicas live under')
    backup.add_argument('--mount-root', default='/run/offsite-restic')
    backup.add_argument('--limit-upload', type=int, default=0, help='KiB/s, 0 for unlimited')
    backup.add_argument('--keep-daily', type=int, default=7)
    backup.add_argument('--keep-weekly', type=int, default=4)
    backup.add_argument('--keep-monthly', type=int, default=12)
    backup.add_argument('--stale-hours', type=int, default=72)
    backup.add_argument('--mqtt-host', default=None)
    backup.add_argument('--mqtt-topic-prefix', default='homeinfra/monitoring/zfs')
    backup.add_argument('--mqtt-name', default=os.uname().nodename)
    backup.add_argument('--mqtt-expire-after', type=int, default=93600)

    sub.add_parser('prune', help='reclaim space from forgotten snapshots')

    check = sub.add_parser('check', help='verify the repository, reading back a sample')
    check.add_argument('--read-data-subset', default='2%')

    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.command == 'backup':
        return command_backup(args)
    return command_maintain(args)


if __name__ == '__main__':
    sys.exit(main())
