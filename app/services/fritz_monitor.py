import subprocess
from typing import List, Optional

from app.config import get_settings
from app.models.fritz import FritzHostStatus


def _ping_host(host: str, count: int = 1, timeout_seconds: int = 1) -> FritzHostStatus:
    """
    Ping a single host once and return a FritzHostStatus.

    This implementation assumes a Linux-like 'ping' command with options:
      -c <count>  : number of echo requests
      -W <timeout>: timeout in seconds for each reply

    In case of failure, is_up is False and latency_ms is None.
    """
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), "-W", str(timeout_seconds), host],
            check=False,  # wir werten den Rückgabecode selbst aus
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        # ping-Binary fehlt – das ist ein genereller Umgebungsfehler.
        return FritzHostStatus(
            host=host,
            is_up=False,
            latency_ms=None,
            error="ping binary not found on host system",
        )

    # Rückgabecode 0 bedeutet: mindestens eine Antwort erhalten
    if result.returncode != 0:
        return FritzHostStatus(
            host=host,
            is_up=False,
            latency_ms=None,
            error=f"ping failed with return code {result.returncode}",
        )

    # Latenz aus der Ausgabe extrahieren (einfacher Ansatz):
    # Beispielzeile: "64 bytes from 192.168.178.1: icmp_seq=1 ttl=64 time=2.34 ms"
    latency_ms: Optional[float] = None
    for line in result.stdout.splitlines():
        if "time=" in line and " ms" in line:
            # sehr simple Parsing-Strategie
            try:
                segment = line.split("time=", 1)[1]
                value_str = segment.split(" ", 1)[0]
                latency_ms = float(value_str)
            except (IndexError, ValueError):
                latency_ms = None
            break

    return FritzHostStatus(
        host=host,
        is_up=True,
        latency_ms=latency_ms,
        error=None,
    )


def get_fritz_status() -> List[FritzHostStatus]:
    """
    Collect the status for all configured FritzBox hosts.

    Hosts are taken from Settings.fritzbox_hosts (likely a list of IPs or hostnames).
    If the setting is empty or None, an empty list is returned.
    """
    settings = get_settings()
    hosts = settings.fritzbox_hosts or []

    statuses: List[FritzHostStatus] = []
    for host in hosts:
        status = _ping_host(host)
        statuses.append(status)

    return statuses

