"""
Metrics Router - Prometheus metrics endpoint

Exposes ZFS metrics in Prometheus text exposition format.
"""
import os
import logging
from fastapi import APIRouter, Response
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST, REGISTRY
from utils.zfs_commands import get_pool_list, get_zfs_version
from utils.parsers import parse_zpool_status

logger = logging.getLogger(__name__)
router = APIRouter()

# Get hostname for metric labels
HOSTNAME = os.getenv("HOSTNAME", "unknown")

# Define Prometheus metrics
# Pool metrics
pool_health_metric = Gauge('zfs_pool_health', 'ZFS pool health status (1=ONLINE, 0=other)',
                           ['hostname', 'pool', 'state'], registry=REGISTRY)
pool_capacity_percent = Gauge('zfs_pool_capacity_percent', 'ZFS pool capacity percentage',
                              ['hostname', 'pool'], registry=REGISTRY)
pool_size_bytes = Gauge('zfs_pool_size_bytes', 'ZFS pool total size in bytes',
                        ['hostname', 'pool'], registry=REGISTRY)
pool_allocated_bytes = Gauge('zfs_pool_allocated_bytes', 'ZFS pool allocated bytes',
                             ['hostname', 'pool'], registry=REGISTRY)
pool_free_bytes = Gauge('zfs_pool_free_bytes', 'ZFS pool free bytes',
                        ['hostname', 'pool'], registry=REGISTRY)
pool_fragmentation_percent = Gauge('zfs_pool_fragmentation_percent', 'ZFS pool fragmentation percentage',
                                   ['hostname', 'pool'], registry=REGISTRY)

# Dataset metrics
dataset_used_bytes = Gauge('zfs_dataset_used_bytes', 'ZFS dataset used bytes',
                           ['hostname', 'pool', 'dataset'], registry=REGISTRY)
dataset_available_bytes = Gauge('zfs_dataset_available_bytes', 'ZFS dataset available bytes',
                                ['hostname', 'pool', 'dataset'], registry=REGISTRY)
dataset_referenced_bytes = Gauge('zfs_dataset_referenced_bytes', 'ZFS dataset referenced bytes',
                                 ['hostname', 'pool', 'dataset'], registry=REGISTRY)

# Snapshot compliance metrics
snapshot_count = Gauge('zfs_snapshot_count', 'Number of snapshots',
                       ['hostname', 'pool', 'dataset', 'policy', 'interval'], registry=REGISTRY)
snapshot_retention = Gauge('zfs_snapshot_retention', 'Snapshot retention target',
                           ['hostname', 'pool', 'dataset', 'policy', 'interval'], registry=REGISTRY)
snapshot_compliance_percent = Gauge('zfs_snapshot_compliance_percent', 'Snapshot policy compliance percentage',
                                    ['hostname', 'pool', 'dataset', 'policy', 'interval'], registry=REGISTRY)


def collect_pool_metrics():
    """Collect and update pool metrics"""
    try:
        pools = get_pool_list()

        for pool in pools:
            pool_name = pool['name']
            health_state = pool.get('health', 'UNKNOWN')

            # Pool health (1 for ONLINE, 0 for anything else)
            health_value = 1 if health_state == 'ONLINE' else 0
            pool_health_metric.labels(hostname=HOSTNAME, pool=pool_name, state=health_state).set(health_value)

            # Pool capacity
            if 'capacity_percent' in pool:
                pool_capacity_percent.labels(hostname=HOSTNAME, pool=pool_name).set(pool['capacity_percent'])

            # Pool sizes
            if 'size_bytes' in pool:
                pool_size_bytes.labels(hostname=HOSTNAME, pool=pool_name).set(pool['size_bytes'])
            if 'allocated_bytes' in pool:
                pool_allocated_bytes.labels(hostname=HOSTNAME, pool=pool_name).set(pool['allocated_bytes'])
            if 'free_bytes' in pool:
                pool_free_bytes.labels(hostname=HOSTNAME, pool=pool_name).set(pool['free_bytes'])
            if 'fragmentation_percent' in pool:
                pool_fragmentation_percent.labels(hostname=HOSTNAME, pool=pool_name).set(pool['fragmentation_percent'])

    except Exception as e:
        logger.error(f"Error collecting pool metrics: {e}")


def collect_dataset_metrics():
    """Collect and update dataset metrics"""
    try:
        # Import here to avoid circular dependency
        from utils.zfs_commands import get_dataset_list

        datasets = get_dataset_list()

        for dataset in datasets:
            dataset_name = dataset['name']
            # Extract pool name (first part before /)
            pool_name = dataset_name.split('/')[0]
            # Dataset name without pool
            dataset_short = dataset_name[len(pool_name)+1:] if '/' in dataset_name else ''

            # Dataset space usage
            if 'used_bytes' in dataset:
                dataset_used_bytes.labels(hostname=HOSTNAME, pool=pool_name, dataset=dataset_short).set(dataset['used_bytes'])
            if 'available_bytes' in dataset:
                dataset_available_bytes.labels(hostname=HOSTNAME, pool=pool_name, dataset=dataset_short).set(dataset['available_bytes'])
            if 'referenced_bytes' in dataset:
                dataset_referenced_bytes.labels(hostname=HOSTNAME, pool=pool_name, dataset=dataset_short).set(dataset['referenced_bytes'])

    except Exception as e:
        logger.error(f"Error collecting dataset metrics: {e}")


def collect_snapshot_metrics():
    """Collect and update snapshot compliance metrics"""
    try:
        # Import the snapshot report function
        from utils.zfs_commands import run_zfs_snapshot_report

        report_data = run_zfs_snapshot_report()
        if not report_data:
            return

        for dataset_info in report_data:
            dataset_name = dataset_info['dataset']
            # Extract pool name
            pool_name = dataset_name.split('/')[0]
            # Dataset name without pool
            dataset_short = dataset_name[len(pool_name)+1:] if '/' in dataset_name else ''

            policy = dataset_info.get('policy', 'unknown')
            counts = dataset_info.get('counts', {})
            retention = dataset_info.get('retention', {})

            # Calculate compliance percentages (same as snapshots router)
            compliance = {}
            for snap_type in ['hourly', 'daily', 'monthly', 'yearly']:
                count = counts.get(snap_type, 0)
                retention_target = retention.get(snap_type, 0)
                compliance[snap_type] = (
                    int(count / retention_target * 100) if retention_target > 0 else 100
                )

            # Iterate through intervals (hourly, daily, monthly, yearly)
            for interval in ['hourly', 'daily', 'monthly', 'yearly']:
                if interval in counts:
                    snapshot_count.labels(
                        hostname=HOSTNAME,
                        pool=pool_name,
                        dataset=dataset_short,
                        policy=policy,
                        interval=interval
                    ).set(counts[interval])

                if interval in retention:
                    snapshot_retention.labels(
                        hostname=HOSTNAME,
                        pool=pool_name,
                        dataset=dataset_short,
                        policy=policy,
                        interval=interval
                    ).set(retention[interval])

                if interval in compliance:
                    snapshot_compliance_percent.labels(
                        hostname=HOSTNAME,
                        pool=pool_name,
                        dataset=dataset_short,
                        policy=policy,
                        interval=interval
                    ).set(compliance[interval])

    except Exception as e:
        logger.error(f"Error collecting snapshot metrics: {e}")


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns ZFS metrics in Prometheus text exposition format for scraping
    by Prometheus, VictoriaMetrics, or other compatible monitoring systems.

    Metrics include:
    - Pool health, capacity, and fragmentation
    - Dataset space usage
    - Snapshot policy compliance
    """
    # Collect all metrics
    collect_pool_metrics()
    collect_dataset_metrics()
    collect_snapshot_metrics()

    # Generate Prometheus text format
    metrics_output = generate_latest(REGISTRY)

    return Response(content=metrics_output, media_type=CONTENT_TYPE_LATEST)
