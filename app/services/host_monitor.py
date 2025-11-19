import socket
import time

import psutil

from app.models.host import HostStatus


def get_host_status() -> HostStatus:
    """
    Collect current host metrics and return them as a HostStatus domain object.

    This function encapsulates all direct calls to psutil/socket/time so that
    the API layer only needs to orchestrate and return a HostStatus instance.
    """
    boot_time = psutil.boot_time()
    uptime_seconds = int(time.time() - boot_time)

    return HostStatus(
        hostname=socket.gethostname(),
        uptime_seconds=uptime_seconds,
        cpu_load_percent=psutil.cpu_percent(interval=0.1),
        memory_used_percent=psutil.virtual_memory().percent,
        disk_used_percent=psutil.disk_usage("/").percent,
    )

