"""
Snapshot Router - API endpoints for ZFS snapshot information

This router provides snapshot status using the zfs-snapshot-report tool,
which includes policy-aware compliance metrics.
"""
import os
import socket
from datetime import datetime
from fastapi import APIRouter, HTTPException
from utils.zfs_commands import (
    run_zfs_snapshot_report,
    get_dataset_snapshots,
    get_all_snapshots
)
from utils.parsers import format_bytes, format_timestamp

router = APIRouter()


@router.get("")
async def get_snapshot_report():
    """
    Get comprehensive snapshot report across all datasets.

    Uses the zfs-snapshot-report tool to provide policy-aware
    snapshot status including compliance metrics for each dataset.

    Returns:
    - Per-dataset snapshot counts by type (hourly/daily/monthly/yearly)
    - Retention policy requirements
    - Compliance percentages
    - Summary statistics
    """
    try:
        report_data = run_zfs_snapshot_report()

        # Enhance with compliance percentages and totals
        for ds in report_data:
            compliance = {}
            for snap_type in ['hourly', 'daily', 'monthly', 'yearly']:
                count = ds['counts'][snap_type]
                retention = ds['retention'][snap_type]
                compliance[snap_type] = (
                    int(count / retention * 100) if retention > 0 else 100
                )
            ds['compliance'] = compliance
            ds['total_snapshots'] = sum(ds['counts'].values())

        # Calculate summary statistics
        total_snapshots = sum(ds['total_snapshots'] for ds in report_data)

        # Calculate average compliance across all policies
        avg_compliance = 0
        if report_data:
            all_compliances = []
            for ds in report_data:
                # Get average compliance for this dataset
                ds_compliances = [v for v in ds['compliance'].values() if v > 0]
                if ds_compliances:
                    all_compliances.extend(ds_compliances)

            if all_compliances:
                avg_compliance = int(sum(all_compliances) / len(all_compliances))

        # Identify datasets with low compliance
        low_compliance_datasets = [
            {
                "dataset": ds["dataset"],
                "policy": ds["policy"],
                "avg_compliance": int(sum(ds['compliance'].values()) / len(ds['compliance']))
            }
            for ds in report_data
            if any(v < 80 for v in ds['compliance'].values())
        ]

        return {
            "hostname": os.getenv("HOSTNAME", socket.gethostname()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "datasets": report_data,
            "summary": {
                "total_datasets": len(report_data),
                "total_snapshots": total_snapshots,
                "avg_compliance": avg_compliance,
                "low_compliance_count": len(low_compliance_datasets)
            },
            "alerts": {
                "low_compliance_datasets": low_compliance_datasets
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset:path}")
async def get_dataset_snapshots_detail(dataset: str):
    """
    Get detailed snapshot list for a specific dataset.

    Args:
        dataset: Name of the dataset (can include slashes)

    Returns:
    - List of all snapshots with creation times and sizes
    - Snapshot count and total space used
    """
    try:
        snapshots = get_dataset_snapshots(dataset)

        # Enhance with human-readable data
        for snapshot in snapshots:
            snapshot["used_human"] = format_bytes(snapshot["used_bytes"])
            snapshot["referenced_human"] = format_bytes(snapshot["referenced_bytes"])
            snapshot["creation_iso"] = format_timestamp(snapshot["creation_timestamp"])

        # Calculate total space used by snapshots
        total_used_bytes = sum(s["used_bytes"] for s in snapshots)

        return {
            "dataset": dataset,
            "snapshot_count": len(snapshots),
            "total_used_bytes": total_used_bytes,
            "total_used_human": format_bytes(total_used_bytes),
            "snapshots": snapshots
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/_all")
async def get_all_snapshots_list():
    """
    Get all snapshots across all datasets.

    Returns a complete list of every snapshot in the system,
    useful for global snapshot analysis.
    """
    try:
        snapshots = get_all_snapshots()

        # Enhance with human-readable data
        for snapshot in snapshots:
            snapshot["used_human"] = format_bytes(snapshot["used_bytes"])
            snapshot["referenced_human"] = format_bytes(snapshot["referenced_bytes"])
            snapshot["creation_iso"] = format_timestamp(snapshot["creation_timestamp"])

        # Calculate totals
        total_used_bytes = sum(s["used_bytes"] for s in snapshots)

        # Group by dataset for summary
        datasets = {}
        for snapshot in snapshots:
            ds_name = snapshot["dataset"]
            if ds_name not in datasets:
                datasets[ds_name] = 0
            datasets[ds_name] += 1

        return {
            "snapshot_count": len(snapshots),
            "dataset_count": len(datasets),
            "total_used_bytes": total_used_bytes,
            "total_used_human": format_bytes(total_used_bytes),
            "snapshots_by_dataset": datasets,
            "snapshots": snapshots
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
