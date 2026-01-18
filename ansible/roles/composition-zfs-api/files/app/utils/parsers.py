"""
ZFS Output Parsers

This module provides parsers for ZFS command outputs, converting
raw text output into structured data.
"""
import re
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_zpool_status(status_output: str) -> Dict:
    """
    Parse zpool status output into structured data.

    Args:
        status_output: Raw output from 'zpool status'

    Returns:
        Structured dictionary with pool status information
    """
    if not status_output:
        return {}

    lines = status_output.strip().split('\n')
    result = {
        "pool": None,
        "state": None,
        "status": None,
        "action": None,
        "scan": {},
        "config": [],
        "errors": None
    }

    current_section = None
    config_lines = []

    for line in lines:
        line_stripped = line.strip()

        # Pool name
        if line.startswith('  pool:'):
            result["pool"] = line.split(':', 1)[1].strip()

        # State
        elif line.startswith(' state:'):
            result["state"] = line.split(':', 1)[1].strip()

        # Status message
        elif line.startswith('status:'):
            result["status"] = line.split(':', 1)[1].strip()

        # Action recommendation
        elif line.startswith('action:'):
            result["action"] = line.split(':', 1)[1].strip()

        # Scan information
        elif line.startswith('  scan:') or line.startswith(' scan:'):
            scan_text = line.split(':', 1)[1].strip()
            result["scan"] = parse_scan_line(scan_text)

        # Config section
        elif line.startswith('config:'):
            current_section = 'config'

        # Errors line
        elif line.startswith('errors:'):
            result["errors"] = line.split(':', 1)[1].strip()

        # Config data
        elif current_section == 'config' and line_stripped:
            # Skip the header line
            if 'NAME' not in line and 'STATE' not in line:
                config_lines.append(line)

    # Parse config lines
    if config_lines:
        result["config"] = parse_config_lines(config_lines)

    return result


def parse_scan_line(scan_text: str) -> Dict:
    """
    Parse scan information from zpool status.

    Args:
        scan_text: Scan line text

    Returns:
        Dictionary with scan information
    """
    scan_info = {}

    if "none requested" in scan_text.lower():
        scan_info["status"] = "none requested"
        return scan_info

    if "scrub" in scan_text.lower():
        scan_info["type"] = "scrub"
    elif "resilver" in scan_text.lower():
        scan_info["type"] = "resilver"

    if "in progress" in scan_text.lower():
        scan_info["status"] = "in progress"
    elif "completed" in scan_text.lower():
        scan_info["status"] = "completed"
    elif "canceled" in scan_text.lower():
        scan_info["status"] = "canceled"

    # Extract error count
    errors_match = re.search(r'with (\d+) errors', scan_text)
    if errors_match:
        scan_info["errors"] = int(errors_match.group(1))
    else:
        scan_info["errors"] = 0

    return scan_info


def parse_config_lines(config_lines: List[str]) -> List[Dict]:
    """
    Parse config section from zpool status.

    Args:
        config_lines: Lines from config section

    Returns:
        List of device configuration dictionaries
    """
    devices = []

    for line in config_lines:
        # Skip empty lines
        if not line.strip():
            continue

        # Parse device line
        parts = line.split()
        if len(parts) >= 2:
            device = {
                "name": parts[0].strip(),
                "state": parts[1].strip()
            }

            # Extract error counts if present
            if len(parts) >= 5:
                try:
                    device["read_errors"] = int(parts[2])
                    device["write_errors"] = int(parts[3])
                    device["checksum_errors"] = int(parts[4])
                except ValueError:
                    pass

            devices.append(device)

    return devices


def format_bytes(bytes_value: int) -> str:
    """
    Format bytes into human-readable string.

    Args:
        bytes_value: Size in bytes

    Returns:
        Human-readable size string (e.g., "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} EB"


def format_timestamp(timestamp: int) -> str:
    """
    Format Unix timestamp to ISO 8601 string.

    Args:
        timestamp: Unix timestamp

    Returns:
        ISO 8601 formatted datetime string
    """
    try:
        dt = datetime.utcfromtimestamp(timestamp)
        return dt.isoformat() + 'Z'
    except (ValueError, OSError):
        return "Invalid timestamp"


def calculate_compression_savings(compression_ratio: str) -> Optional[float]:
    """
    Calculate space savings percentage from compression ratio.

    Args:
        compression_ratio: Compression ratio string (e.g., "2.50x")

    Returns:
        Space savings as percentage, or None if invalid
    """
    try:
        # Remove 'x' suffix and convert to float
        ratio = float(compression_ratio.rstrip('x'))
        if ratio > 1.0:
            savings = (1 - (1 / ratio)) * 100
            return round(savings, 2)
    except (ValueError, ZeroDivisionError):
        pass
    return None
