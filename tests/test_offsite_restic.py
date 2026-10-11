from datetime import datetime

from offsite_restic import (
    backup_command,
    build_status,
    forget_command,
    latest_offsite_times,
    latest_snapshot,
    mount_point,
    needs_backup,
    replica_path,
    smallest_first,
    split_target,
)


# ---------------------------------------------------------------------------
# Naming: a target is "<client>/<dataset>", exactly as the ZFS push role
# already spells it, and everything else is derived from that one string.
# ---------------------------------------------------------------------------


def test_target_splits_into_client_and_dataset():
    assert split_target('server-64gb-storage/slowpool/charlie/photos') == (
        'server-64gb-storage',
        'slowpool/charlie/photos',
    )


def test_replica_path_sits_under_the_replica_root():
    assert replica_path('slowpool/backups/raw', 'server-64gb-storage/slowpool/charlie') == (
        'slowpool/backups/raw/server-64gb-storage/slowpool/charlie'
    )


def test_mount_point_is_stable_for_a_target():
    # restic finds the parent snapshot by host and path, so the path must not
    # change between runs or every run re-reads every file.
    assert mount_point('/run/offsite-restic', 'storage/slowpool/charlie/photos') == (
        '/run/offsite-restic/storage/slowpool/charlie/photos'
    )


# ---------------------------------------------------------------------------
# Choosing the snapshot to read
# ---------------------------------------------------------------------------


def test_latest_snapshot_is_the_newest_by_creation_not_by_name():
    listing = (
        'pool/ds@autosnap_2026-10-11_14:00:26_hourly\t1791720026\n'
        'pool/ds@zzz_manual\t1791000000\n'
        'pool/ds@autosnap_2026-10-11_16:00:15_hourly\t1791727215\n'
    )
    assert latest_snapshot(listing) == (
        'pool/ds@autosnap_2026-10-11_16:00:15_hourly',
        1791727215,
    )


def test_latest_snapshot_of_a_dataset_with_none_is_none():
    assert latest_snapshot('') is None
    assert latest_snapshot('\n') is None


# ---------------------------------------------------------------------------
# Ordering: the first run uploads for days. The small, irreplaceable datasets
# must not queue behind the photo library.
# ---------------------------------------------------------------------------


def test_smallest_dataset_goes_first():
    sizes = {'c/photos': 370_000_000_000, 'c/financial': 7_000_000, 'c/music': 33_000_000_000}
    assert smallest_first(sizes) == ['c/financial', 'c/music', 'c/photos']


# ---------------------------------------------------------------------------
# restic invocations
# ---------------------------------------------------------------------------


def test_backup_command_records_client_and_snapshot():
    cmd = backup_command(
        target='storage/slowpool/charlie/financial',
        mount='/run/offsite-restic/storage/slowpool/charlie/financial',
        snapshot='slowpool/backups/raw/storage/slowpool/charlie/financial@autosnap_x',
        created=datetime(2026, 10, 11, 16, 0, 15),
        limit_upload_kib=1000,
    )
    assert cmd[:2] == ['restic', 'backup']
    assert cmd[-1] == '/run/offsite-restic/storage/slowpool/charlie/financial'
    assert cmd[cmd.index('--host') + 1] == 'storage'
    assert cmd[cmd.index('--time') + 1] == '2026-10-11 16:00:15'
    assert cmd[cmd.index('--limit-upload') + 1] == '1000'
    assert 'zfs=autosnap_x' in cmd
    assert '--one-file-system' in cmd


def test_backup_command_without_a_limit_leaves_the_flag_out():
    cmd = backup_command(
        target='storage/pool/ds',
        mount='/m',
        snapshot='r/storage/pool/ds@s',
        created=datetime(2026, 1, 1),
        limit_upload_kib=0,
    )
    assert '--limit-upload' not in cmd


def test_forget_keeps_the_stated_retention_and_does_not_prune():
    cmd = forget_command({'daily': 7, 'weekly': 4, 'monthly': 12})
    assert cmd[:2] == ['restic', 'forget']
    assert cmd[cmd.index('--keep-daily') + 1] == '7'
    assert cmd[cmd.index('--keep-weekly') + 1] == '4'
    assert cmd[cmd.index('--keep-monthly') + 1] == '12'
    assert cmd[cmd.index('--group-by') + 1] == 'host,paths'
    # Pruning rewrites packs over a slow uplink; it has its own schedule.
    assert '--prune' not in cmd


# ---------------------------------------------------------------------------
# What is already offsite
# ---------------------------------------------------------------------------

REPO = [
    {'hostname': 'storage', 'paths': ['/run/offsite-restic/storage/pool/a'], 'time': '2026-10-10T16:00:15+02:00'},
    {'hostname': 'storage', 'paths': ['/run/offsite-restic/storage/pool/a'], 'time': '2026-10-11T16:00:15.123456789+02:00'},
    {'hostname': 'storage', 'paths': ['/run/offsite-restic/storage/pool/b'], 'time': '2026-10-01T00:00:00Z'},
]


def test_latest_offsite_time_is_per_target():
    times = latest_offsite_times(REPO, '/run/offsite-restic')
    # restic prints nanoseconds, which datetime cannot parse as written.
    assert times['storage/pool/a'] == datetime.fromisoformat('2026-10-11T16:00:15.123456+02:00').timestamp()
    assert times['storage/pool/b'] == datetime.fromisoformat('2026-10-01T00:00:00+00:00').timestamp()
    assert 'storage/pool/c' not in times


def test_snapshot_already_offsite_is_not_sent_again():
    # A run that died half way restarts from the top; the datasets it finished
    # must cost one comparison, not another read of every file.
    assert needs_backup(snapshot_created=1000, offsite_time=1000) is False
    assert needs_backup(snapshot_created=1000, offsite_time=2000) is False
    assert needs_backup(snapshot_created=1000, offsite_time=999) is True
    assert needs_backup(snapshot_created=1000, offsite_time=None) is True


# ---------------------------------------------------------------------------
# Status: absent, late and failed are three different problems.
# ---------------------------------------------------------------------------

NOW = datetime(2026, 10, 12, 12, 0, 0).timestamp()


def test_status_is_ok_only_when_every_target_is_fresh():
    status = build_status(
        targets=['s/a', 's/b'],
        offsite={'s/a': NOW - 3600, 's/b': NOW - 7200},
        failures={},
        now=NOW,
        stale_hours=72,
        running=False,
    )
    assert status['ok'] is True
    assert status['healthy_datasets'] == ['s/a', 's/b']


def test_target_never_sent_is_missing_not_stale():
    status = build_status(
        targets=['s/a', 's/b'],
        offsite={'s/a': NOW - 3600},
        failures={},
        now=NOW,
        stale_hours=72,
        running=True,
    )
    assert status['ok'] is False
    assert status['missing_datasets'] == ['s/b']
    assert status['stale_datasets'] == []
    assert status['running'] is True


def test_old_copy_is_stale():
    status = build_status(
        targets=['s/a'],
        offsite={'s/a': NOW - 73 * 3600},
        failures={},
        now=NOW,
        stale_hours=72,
        running=False,
    )
    assert status['ok'] is False
    assert status['stale_datasets'] == ['s/a']


def test_failure_is_reported_even_when_an_older_copy_is_still_fresh():
    status = build_status(
        targets=['s/a'],
        offsite={'s/a': NOW - 3600},
        failures={'s/a': 'restic exited 1'},
        now=NOW,
        stale_hours=72,
        running=False,
    )
    assert status['ok'] is False
    assert status['failures'] == {'s/a': 'restic exited 1'}
