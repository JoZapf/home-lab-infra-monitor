from fastapi import APIRouter

from app.models.host import HostStatus
from app.services.host_monitor import get_host_status

router = APIRouter()


@router.get("/status", response_model=HostStatus, summary="Hoststatus")
async def host_status() -> HostStatus:
    """
    Return the current host status.

    This endpoint delegates all data collection to the host_monitor service and
    only returns a HostStatus model instance, which FastAPI serialises to JSON.
    """
    return get_host_status()

