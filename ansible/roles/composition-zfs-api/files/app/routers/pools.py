"""
Pool Router - API endpoints for ZFS pool information
"""
from fastapi import APIRouter, HTTPException
from utils.zfs_commands import (
    get_pool_list,
    get_pool_status,
    get_pool_iostat,
    get_zfs_version
)
from utils.parsers import parse_zpool_status, format_bytes

router = APIRouter()


@router.get("")
async def list_pools():
    """
    List all ZFS pools with basic metrics.

    Returns information about all pools including health status,
    capacity, and fragmentation.
    """
    try:
        pools = get_pool_list()

        # Enhance with human-readable sizes
        for pool in pools:
            pool["size_human"] = format_bytes(pool["size_bytes"])
            pool["allocated_human"] = format_bytes(pool["allocated_bytes"])
            pool["free_human"] = format_bytes(pool["free_bytes"])

        return {
            "pools": pools,
            "count": len(pools)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pool_name}")
async def get_pool_info(pool_name: str):
    """
    Get detailed information for a specific pool.

    Args:
        pool_name: Name of the pool

    Returns detailed metrics and status for the specified pool.
    """
    try:
        # Get pool list to find the specific pool
        pools = get_pool_list()
        pool = next((p for p in pools if p["name"] == pool_name), None)

        if not pool:
            raise HTTPException(status_code=404, detail=f"Pool '{pool_name}' not found")

        # Add human-readable sizes
        pool["size_human"] = format_bytes(pool["size_bytes"])
        pool["allocated_human"] = format_bytes(pool["allocated_bytes"])
        pool["free_human"] = format_bytes(pool["free_bytes"])

        return pool
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pool_name}/status")
async def get_pool_status_detail(pool_name: str):
    """
    Get detailed status for a specific pool.

    Args:
        pool_name: Name of the pool

    Returns comprehensive status information including:
    - Pool state
    - Device configuration
    - Scrub/resilver status
    - Error counts
    """
    try:
        status_output = get_pool_status(pool_name)

        if not status_output:
            raise HTTPException(
                status_code=404,
                detail=f"Could not get status for pool '{pool_name}'"
            )

        # Parse the status output
        parsed_status = parse_zpool_status(status_output)

        # Add raw output for debugging/reference
        parsed_status["raw_output"] = status_output

        return parsed_status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pool_name}/iostat")
async def get_pool_iostat_detail(pool_name: str):
    """
    Get I/O statistics for a specific pool.

    Args:
        pool_name: Name of the pool

    Returns I/O statistics for the pool and its devices.
    """
    try:
        iostat_output = get_pool_iostat(pool_name)

        if not iostat_output:
            raise HTTPException(
                status_code=404,
                detail=f"Could not get I/O stats for pool '{pool_name}'"
            )

        # Return raw output for now
        # TODO: Parse iostat output into structured format
        return {
            "pool": pool_name,
            "iostat": iostat_output
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/_version")
async def get_version():
    """
    Get ZFS version information.

    Returns the installed ZFS version.
    """
    try:
        version = get_zfs_version()

        if not version:
            raise HTTPException(status_code=500, detail="Could not get ZFS version")

        return {
            "version": version
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
