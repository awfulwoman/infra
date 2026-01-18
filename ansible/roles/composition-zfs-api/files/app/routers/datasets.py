"""
Dataset Router - API endpoints for ZFS dataset information
"""
from fastapi import APIRouter, HTTPException
from utils.zfs_commands import (
    get_dataset_list,
    get_dataset_properties,
    get_dataset_snapshots
)
from utils.parsers import (
    format_bytes,
    calculate_compression_savings
)

router = APIRouter()


@router.get("")
async def list_datasets():
    """
    List all ZFS datasets with properties.

    Returns information about all datasets including space usage,
    compression, and mount points.
    """
    try:
        datasets = get_dataset_list()

        # Enhance with human-readable data
        for dataset in datasets:
            dataset["used_human"] = format_bytes(dataset["used_bytes"])
            dataset["available_human"] = format_bytes(dataset["available_bytes"])
            dataset["referenced_human"] = format_bytes(dataset["referenced_bytes"])

            # Calculate compression savings
            if dataset["compression_ratio"]:
                savings = calculate_compression_savings(dataset["compression_ratio"])
                if savings:
                    dataset["compression_savings_percent"] = savings

        return {
            "datasets": datasets,
            "count": len(datasets)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_name:path}")
async def get_dataset_info(dataset_name: str):
    """
    Get detailed information for a specific dataset.

    Args:
        dataset_name: Name of the dataset (can include slashes)

    Returns detailed properties for the specified dataset.
    """
    try:
        # Get all properties for the dataset
        properties = get_dataset_properties(dataset_name)

        if not properties:
            raise HTTPException(
                status_code=404,
                detail=f"Dataset '{dataset_name}' not found"
            )

        # Extract and format key properties
        result = {
            "name": dataset_name,
            "properties": properties
        }

        # Add human-readable values for key numeric properties
        if "used" in properties:
            try:
                result["used_human"] = format_bytes(int(properties["used"]))
            except ValueError:
                pass

        if "available" in properties:
            try:
                result["available_human"] = format_bytes(int(properties["available"]))
            except ValueError:
                pass

        if "referenced" in properties:
            try:
                result["referenced_human"] = format_bytes(int(properties["referenced"]))
            except ValueError:
                pass

        # Compression savings
        if "compressratio" in properties:
            savings = calculate_compression_savings(properties["compressratio"])
            if savings:
                result["compression_savings_percent"] = savings

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_name:path}/snapshots")
async def get_dataset_snapshots_list(dataset_name: str):
    """
    Get all snapshots for a specific dataset.

    Args:
        dataset_name: Name of the dataset (can include slashes)

    Returns list of snapshots for the specified dataset.
    """
    try:
        snapshots = get_dataset_snapshots(dataset_name)

        # Enhance with human-readable data
        for snapshot in snapshots:
            snapshot["used_human"] = format_bytes(snapshot["used_bytes"])
            snapshot["referenced_human"] = format_bytes(snapshot["referenced_bytes"])

            # Format timestamp
            from utils.parsers import format_timestamp
            snapshot["creation_iso"] = format_timestamp(snapshot["creation_timestamp"])

        return {
            "dataset": dataset_name,
            "snapshots": snapshots,
            "count": len(snapshots)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
