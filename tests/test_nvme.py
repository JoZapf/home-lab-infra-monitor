from fastapi.testclient import TestClient

from app.main import app
from app.models.nvme import NvmeDeviceStatus
from app.services import nvme_monitor

client = TestClient(app)


def test_get_nvme_status_uses_devices_from_settings(monkeypatch):
    """
    Unit-test for the service layer: ensure that get_nvme_status reads the
    list of devices from Settings and turns them into NvmeDeviceStatus
    instances with the correct critical flag.
    """

    class DummySettings:
        nvme_devices = ["/dev/nvme0n1", "/dev/nvme1n1"]

    def fake_get_settings():
        return DummySettings()

    def fake_read_temperature(device: str) -> float:
        if device == "/dev/nvme0n1":
            return 45.0
        if device == "/dev/nvme1n1":
            return 80.0
        raise AssertionError(f"Unexpected device {device!r} in test")

    # Patch settings + low-level temperature reader
    monkeypatch.setattr(nvme_monitor, "get_settings", fake_get_settings)
    monkeypatch.setattr(
        nvme_monitor,
        "_read_nvme_temperature",
        fake_read_temperature,
    )

    statuses = nvme_monitor.get_nvme_status()

    assert len(statuses) == 2

    first, second = statuses
    assert isinstance(first, NvmeDeviceStatus)
    assert first.device == "/dev/nvme0n1"
    assert first.temperature_celsius == 45.0
    assert first.is_critical is False

    assert second.device == "/dev/nvme1n1"
    assert second.temperature_celsius == 80.0
    assert second.is_critical is True


def test_nvme_status_endpoint_structure(monkeypatch):
    """
    Integration-style test for the /nvme/status endpoint:
    monkeypatch the service layer and assert response structure & values.
    """

    fake_data = [
        NvmeDeviceStatus(
            device="/dev/nvme0n1",
            temperature_celsius=40.0,
            is_critical=False,
        ),
        NvmeDeviceStatus(
            device="/dev/nvme1n1",
            temperature_celsius=75.0,
            is_critical=True,
        ),
    ]

    def fake_get_nvme_status():
        return fake_data

    # Patch service function used by the API router
    monkeypatch.setattr(
        nvme_monitor,
        "get_nvme_status",
        fake_get_nvme_status,
    )

    response = client.get("/nvme/status")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2

    first, second = data

    # Basic type + structure checks
    assert first["device"] == "/dev/nvme0n1"
    assert isinstance(first["temperature_celsius"], (int, float))
    assert first["is_critical"] is False

    assert second["device"] == "/dev/nvme1n1"
    assert isinstance(second["temperature_celsius"], (int, float))
    assert second["is_critical"] is True


def test_nvme_status_endpoint_error_maps_to_503(monkeypatch):
    """
    Wenn der NVMe-Service einen RuntimeError wirft, soll der Endpoint
    einen HTTP 503 Service Unavailable zurückgeben und die Fehlermeldung
    im JSON-Body (detail) transportieren.
    """

    def fake_get_nvme_status():
        raise RuntimeError("nvme-cli binary not found; install nvme-cli on the host")

    # Patcht die vom Endpoint verwendete Service-Funktion
    monkeypatch.setattr(
        nvme_monitor,
        "get_nvme_status",
        fake_get_nvme_status,
    )

    response = client.get("/nvme/status")

    assert response.status_code == 503

    body = response.json()
    assert "detail" in body
    assert "nvme-cli binary not found" in body["detail"]

