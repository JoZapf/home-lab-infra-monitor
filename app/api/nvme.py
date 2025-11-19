from typing import List

from fastapi import APIRouter, HTTPException

from app.models.nvme import NvmeDeviceStatus
from app.services import nvme_monitor

router = APIRouter()


@router.get(
    "/status",
    response_model=List[NvmeDeviceStatus],
    summary="NVMe status",
)
async def nvme_status() -> List[NvmeDeviceStatus]:
    """
    Return the status (temperature and simple critical flag) for all NVMe
    devices configured in Settings.nvme_devices (env var NVME_DEVICES).

    In case of NVMe-related runtime errors (e.g. nvme-cli not installed or
    smart-log parsing issues), a HTTP 503 Service Unavailable is returned.
    """
    try:
        return nvme_monitor.get_nvme_status()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

