from fastapi.testclient import TestClient

from app.main import app
from app.models.fritz import FritzHostStatus
from app.services import fritz_monitor

client = TestClient(app)


def test_get_fritz_status_uses_hosts_from_settings(monkeypatch):
    """
    Unit-Test für den Service-Layer:
    - get_fritz_status liest FritzBox-Hosts aus den Settings
    - _ping_host wird pro Host aufgerufen
    - es werden FritzHostStatus-Objekte zurückgegeben
    """

    class DummySettings:
        fritzbox_hosts = ["192.168.178.1", "fritz.box"]

    def fake_get_settings():
        return DummySettings()

    def fake_ping_host(host: str):
        if host == "192.168.178.1":
            return FritzHostStatus(
                host=host,
                is_up=True,
                latency_ms=2.0,
                error=None,
            )
        if host == "fritz.box":
            return FritzHostStatus(
                host=host,
                is_up=False,
                latency_ms=None,
                error="ping failed with return code 1",
            )
        raise AssertionError(f"Unexpected host {host!r} in test")

    monkeypatch.setattr(fritz_monitor, "get_settings", fake_get_settings)
    monkeypatch.setattr(fritz_monitor, "_ping_host", fake_ping_host)

    statuses = fritz_monitor.get_fritz_status()

    assert len(statuses) == 2

    first, second = statuses
    assert isinstance(first, FritzHostStatus)
    assert first.host == "192.168.178.1"
    assert first.is_up is True
    assert first.latency_ms == 2.0
    assert first.error is None

    assert second.host == "fritz.box"
    assert second.is_up is False
    assert second.latency_ms is None
    assert "return code 1" in (second.error or "")

def test_fritz_status_endpoint_structure(monkeypatch):
    """
    Integrationstest für den /fritz/status Endpoint:
    - fritz_monitor.get_fritz_status wird gepatcht
    - Response-Struktur und Werte werden geprüft
    """

    fake_data = [
        FritzHostStatus(
            host="192.168.178.1",
            is_up=True,
            latency_ms=3.5,
            error=None,
        ),
        FritzHostStatus(
            host="fritz.box",
            is_up=False,
            latency_ms=None,
            error="ping failed with return code 1",
        ),
    ]

    def fake_get_fritz_status():
        return fake_data

    monkeypatch.setattr(
        fritz_monitor,
        "get_fritz_status",
        fake_get_fritz_status,
    )

    response = client.get("/fritz/status")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2

    first, second = data

    assert first["host"] == "192.168.178.1"
    assert first["is_up"] is True
    assert isinstance(first["latency_ms"], (int, float))
    assert first["error"] is None

    assert second["host"] == "fritz.box"
    assert second["is_up"] is False
    assert second["latency_ms"] is None
    assert isinstance(second["error"], str)
    assert "return code 1" in second["error"]

def test_ping_binary_missing_sets_error_flag(monkeypatch):
    """
    Wenn das ping-Binary auf dem Host-System fehlt und subprocess.run
    einen FileNotFoundError wirft, soll _ping_host einen FritzHostStatus
    mit is_up=False, latency_ms=None und aussagekräftiger error zurückgeben.
    """

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("ping not found")

    monkeypatch.setattr("app.services.fritz_monitor.subprocess.run", fake_run)

    status = fritz_monitor._ping_host("fritz.box")

    assert status.host == "fritz.box"
    assert status.is_up is False
    assert status.latency_ms is None
    assert isinstance(status.error, str)
    assert "ping binary not found" in status.error

