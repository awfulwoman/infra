"""
Backup Router - API endpoints for ZFS backup status

This router provides information about backup status by examining
backup datasets and logs (if available).
"""
import os
import glob
from datetime import datetime
from fastapi import APIRouter, HTTPException
from utils.zfs_commands import get_dataset_list

router = APIRouter()


@router.get("")
async def get_backup_status():
    """
    Get backup status overview.

    Examines datasets under common backup paths to identify
    backed-up datasets and their status.

    Note: This is a basic implementation that identifies backup
    datasets by naming patterns. Enhanced monitoring can be added
    by parsing backup logs.
    """
    try:
        all_datasets = get_dataset_list()

        # Find datasets that appear to be backups
        # Common patterns: contains '/backups/', contains '/encryptedbackups/'
        backup_datasets = [
            ds for ds in all_datasets
            if '/backups/' in ds['name'] or
               '/encryptedbackups/' in ds['name'] or
               ds['name'].startswith('backups/')
        ]

        # Organize by backup type
        backup_info = {
            "local_backups": [],
            "offsite_backups": []
        }

        for ds in backup_datasets:
            ds_info = {
                "name": ds["name"],
                "used_bytes": ds["used_bytes"],
                "used_human": ds["used_human"],
                "available_bytes": ds["available_bytes"],
                "available_human": ds["available_human"]
            }

            if 'encryptedbackups' in ds['name']:
                backup_info["offsite_backups"].append(ds_info)
            else:
                backup_info["local_backups"].append(ds_info)

        return {
            "backup_datasets": backup_info,
            "total_local_backups": len(backup_info["local_backups"]),
            "total_offsite_backups": len(backup_info["offsite_backups"]),
            "note": "This is a basic overview based on dataset naming patterns. "
                    "For detailed backup logs, check /var/log/zfs-policy/"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs")
async def get_backup_logs():
    """
    Get recent backup log files.

    Returns a list of available backup log files from /var/log/zfs-policy/.

    Note: This only lists available logs. Use /backups/logs/{filename}
    to retrieve actual log content.
    """
    try:
        log_dir = "/var/log/zfs-policy"

        if not os.path.exists(log_dir):
            return {
                "available": False,
                "message": "Backup log directory not found",
                "path": log_dir
            }

        # Find log files
        log_files = []
        for pattern in ['*.log', 'zfs-snapshot-*.log', 'zfs-prune-*.log']:
            log_files.extend(glob.glob(os.path.join(log_dir, pattern)))

        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

        # Get file info
        log_info = []
        for log_file in log_files[:20]:  # Limit to 20 most recent
            stat = os.stat(log_file)
            log_info.append({
                "filename": os.path.basename(log_file),
                "path": log_file,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat() + 'Z'
            })

        return {
            "available": True,
            "log_directory": log_dir,
            "log_count": len(log_info),
            "logs": log_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/{filename}")
async def get_backup_log_content(filename: str, lines: int = 100):
    """
    Get content from a specific backup log file.

    Args:
        filename: Name of the log file
        lines: Number of lines to return (default: 100, max: 1000)

    Returns the last N lines of the specified log file.
    """
    try:
        # Sanitize filename to prevent path traversal
        filename = os.path.basename(filename)
        log_path = os.path.join("/var/log/zfs-policy", filename)

        if not os.path.exists(log_path):
            raise HTTPException(status_code=404, detail=f"Log file '{filename}' not found")

        # Limit lines to prevent excessive data transfer
        lines = min(max(1, lines), 1000)

        # Read last N lines
        try:
            with open(log_path, 'r') as f:
                all_lines = f.readlines()
                content_lines = all_lines[-lines:]

            return {
                "filename": filename,
                "lines_requested": lines,
                "lines_returned": len(content_lines),
                "total_lines": len(all_lines),
                "content": ''.join(content_lines)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading log file: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
