import re
import subprocess
from typing import List

from app.config import get_settings
from app.models.nvme import NvmeDeviceStatus

# Simple regex to extract the line "temperature : 42 C"
_NVME_TEMP_PATTERN = re.compile(r"temperature\s*:\s*(\d+)\s*C", re.IGNORECASE)

# Naive warning threshold – can later be made configurable via Settings
_WARNING_TEMP_C = 70.0


def _read_nvme_temperature(device: str) -> float:
    """
    Read the current temperature of an NVMe device using nvme-cli.

    This function calls `nvme smart-log <device>` and parses the 'temperature'
    line. It raises RuntimeError if nvme-cli is missing or the output cannot
    be parsed.
    """
    try:
        result = subprocess.run(
            ["nvme", "smart-log", device],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "nvme-cli binary not found; install nvme-cli on the host"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"nvme smart-log failed for {device}: {exc.stderr}"
        ) from exc

    match = _NVME_TEMP_PATTERN.search(result.stdout)
    if not match:
        raise RuntimeError(
            f"Could not parse temperature for {device} "
            "from nvme smart-log output"
        )

    return float(match.group(1))


def get_nvme_status() -> List[NvmeDeviceStatus]:
    """
    Collect the current status for all configured NVMe devices.

    Devices are taken from Settings.nvme_devices. If that setting is empty or
    None, an empty list is returned.
    """
    settings = get_settings()
    devices = settings.nvme_devices or []

    statuses: List[NvmeDeviceStatus] = []
    for device in devices:
        temp = _read_nvme_temperature(device)
        statuses.append(
            NvmeDeviceStatus(
                device=device,
                temperature_celsius=temp,
                is_critical=temp >= _WARNING_TEMP_C,
            )
        )

    return statuses

