"""
ZFS Command Execution Module

This module provides functions to execute ZFS commands and retrieve
system information. All operations are read-only.
"""
import subprocess
import json
import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Get command timeout from environment
COMMAND_TIMEOUT = int(os.getenv("ZFS_API_COMMAND_TIMEOUT", "30"))


def run_command(cmd: List[str], timeout: Optional[int] = None) -> Optional[str]:
    """
    Run a command and return stdout, or None on error.

    Args:
        cmd: List of command arguments
        timeout: Command timeout in seconds (uses COMMAND_TIMEOUT if None)

    Returns:
        Command stdout as string, or None on error
    """
    if timeout is None:
        timeout = COMMAND_TIMEOUT

    try:
        logger.debug(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout}s: {' '.join(cmd)}")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error running command: {e}")
        return None


def run_zfs_snapshot_report() -> List[Dict]:
    """
    Get snapshot report data from cache file or run zfs-snapshot-report.

    Tries to read from cache file first for performance. Falls back to
    running the command if cache is missing or invalid.

    Returns:
        List of dataset snapshot information dictionaries

    Raises:
        RuntimeError: If the command fails or output cannot be parsed
    """
    cache_file = os.getenv("ZFS_SNAPSHOT_REPORT_CACHE", "/var/cache/zfs-snapshot-report.json")

    # Try reading from cache first
    try:
        if os.path.exists(cache_file):
            logger.debug(f"Reading snapshot report from cache: {cache_file}")
            with open(cache_file, 'r') as f:
                data = json.load(f)
                # Cache file contains full report structure
                if 'managed' in data:
                    return data['managed']
                return data
    except (IOError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to read cache file {cache_file}: {e}. Falling back to command.")

    # Fallback to running command
    logger.debug("Running zfs-snapshot-report command")
    output = run_command(["/opt/zfs-policy/zfs-snapshot-report", "--json"])
    if not output:
        raise RuntimeError("Failed to get snapshot report")

    try:
        data = json.loads(output)
        # Command returns full report structure
        if 'managed' in data:
            return data['managed']
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse snapshot report JSON: {e}")
        raise RuntimeError("Invalid JSON from snapshot report")


def get_snapshot_report() -> Optional[Dict]:
    """
    Get snapshot policy compliance report from zfs-snapshot-report.

    Returns:
        Dictionary containing snapshot compliance report, or None on error
    """
    try:
        report_data = run_zfs_snapshot_report()
        # The report returns a list, we need to wrap it in a dict with 'datasets' key
        return {"datasets": report_data}
    except Exception as e:
        logger.error(f"Failed to get snapshot report: {e}")
        return None


def get_pool_list() -> List[Dict]:
    """
    Get list of all ZFS pools with basic metrics.

    Returns:
        List of pool information dictionaries
    """
    output = run_command([
        "zpool", "list", "-H", "-p",
        "-o", "name,health,size,alloc,free,cap,frag"
    ])
    if not output:
        return []

    pools = []
    for line in output.splitlines():
        parts = line.split('\t')
        if len(parts) >= 7:
            pools.append({
                "name": parts[0],
                "health": parts[1],
                "size_bytes": int(parts[2]),
                "allocated_bytes": int(parts[3]),
                "free_bytes": int(parts[4]),
                "capacity_percent": int(parts[5]),
                "fragmentation_percent": int(parts[6]) if parts[6] != '-' else None
            })
    return pools


def get_pool_status(pool_name: str) -> Optional[str]:
    """
    Get detailed status for a specific pool.

    Args:
        pool_name: Name of the pool

    Returns:
        Raw zpool status output, or None on error
    """
    return run_command(["zpool", "status", pool_name])


def get_pool_iostat(pool_name: str) -> Optional[str]:
    """
    Get I/O statistics for a specific pool.

    Args:
        pool_name: Name of the pool

    Returns:
        Raw zpool iostat output, or None on error
    """
    return run_command(["zpool", "iostat", "-v", pool_name])


def get_dataset_list() -> List[Dict]:
    """
    Get list of all ZFS datasets with properties.

    Returns:
        List of dataset information dictionaries
    """
    output = run_command([
        "zfs", "list", "-H", "-p",
        "-o", "name,used,avail,refer,mountpoint,compression,compressratio"
    ])
    if not output:
        return []

    datasets = []
    for line in output.splitlines():
        parts = line.split('\t')
        if len(parts) >= 7:
            datasets.append({
                "name": parts[0],
                "used_bytes": int(parts[1]),
                "available_bytes": int(parts[2]),
                "referenced_bytes": int(parts[3]),
                "mountpoint": parts[4],
                "compression": parts[5],
                "compression_ratio": parts[6]
            })
    return datasets


def get_dataset_properties(dataset_name: str) -> Dict[str, str]:
    """
    Get all properties for a specific dataset.

    Args:
        dataset_name: Name of the dataset

    Returns:
        Dictionary of property names to values
    """
    output = run_command([
        "zfs", "get", "-H", "-p", "all", dataset_name
    ])
    if not output:
        return {}

    properties = {}
    for line in output.splitlines():
        parts = line.split('\t')
        if len(parts) >= 3:
            prop_name = parts[1]
            prop_value = parts[2]
            properties[prop_name] = prop_value
    return properties


def get_dataset_snapshots(dataset: str) -> List[Dict]:
    """
    Get all snapshots for a dataset.

    Args:
        dataset: Name of the dataset

    Returns:
        List of snapshot information dictionaries
    """
    output = run_command([
        "zfs", "list", "-t", "snapshot", "-H", "-p",
        "-o", "name,creation,used,referenced",
        "-s", "creation", "-r", dataset
    ])
    if not output:
        return []

    snapshots = []
    for line in output.splitlines():
        parts = line.split('\t')
        if len(parts) >= 4 and parts[0].startswith(f"{dataset}@"):
            snapshot_name = parts[0].split('@')[1]
            snapshots.append({
                "name": snapshot_name,
                "full_name": parts[0],
                "creation_timestamp": int(parts[1]),
                "used_bytes": int(parts[2]),
                "referenced_bytes": int(parts[3])
            })
    return snapshots


def get_all_snapshots() -> List[Dict]:
    """
    Get all snapshots across all datasets.

    Returns:
        List of snapshot information dictionaries
    """
    output = run_command([
        "zfs", "list", "-t", "snapshot", "-H", "-p",
        "-o", "name,creation,used,referenced",
        "-s", "creation"
    ])
    if not output:
        return []

    snapshots = []
    for line in output.splitlines():
        parts = line.split('\t')
        if len(parts) >= 4 and '@' in parts[0]:
            dataset, snapshot_name = parts[0].split('@', 1)
            snapshots.append({
                "dataset": dataset,
                "name": snapshot_name,
                "full_name": parts[0],
                "creation_timestamp": int(parts[1]),
                "used_bytes": int(parts[2]),
                "referenced_bytes": int(parts[3])
            })
    return snapshots


def get_zfs_version() -> Optional[str]:
    """
    Get ZFS version information.

    Returns:
        ZFS version string, or None on error
    """
    output = run_command(["zfs", "version"])
    if output:
        # Extract version from first line (typically "zfs-X.Y.Z-...")
        first_line = output.split('\n')[0]
        return first_line
    return None
