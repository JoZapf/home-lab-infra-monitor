from typing import List

from fastapi import APIRouter

from app.models.fritz import FritzHostStatus
from app.services import fritz_monitor

router = APIRouter()


@router.get(
    "/status",
    response_model=List[FritzHostStatus],
    summary="FritzBox host status",
)
async def fritz_status() -> List[FritzHostStatus]:
    """
    Return reachability and latency information for all configured FritzBox hosts.

    Hosts are taken from Settings.fritzbox_hosts (env var FRITZBOX_HOSTS).
    """
    return fritz_monitor.get_fritz_status()

