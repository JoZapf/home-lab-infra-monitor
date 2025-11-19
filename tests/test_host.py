from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_host_status_endpoint_structure_and_ranges():
    response = client.get("/host/status")
    assert response.status_code == 200

    data = response.json()

    # Expected keys
    expected_keys = {
        "hostname",
        "uptime_seconds",
        "cpu_load_percent",
        "memory_used_percent",
        "disk_used_percent",
    }
    assert expected_keys.issubset(data.keys())

    # Basic type checks
    assert isinstance(data["hostname"], str)
    assert isinstance(data["uptime_seconds"], int)
    assert isinstance(data["cpu_load_percent"], (int, float))
    assert isinstance(data["memory_used_percent"], (int, float))
    assert isinstance(data["disk_used_percent"], (int, float))

    # Value ranges (soft sanity checks, not hard performance tests)
    assert data["uptime_seconds"] >= 0
    assert 0.0 <= data["cpu_load_percent"] <= 100.0
    assert 0.0 <= data["memory_used_percent"] <= 100.0
    assert 0.0 <= data["disk_used_percent"] <= 100.0

    # Minimal structural sanity: hostname should not be empty
    assert data["hostname"].strip() != ""

