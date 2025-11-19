import os

from app.config import Settings, get_settings


def test_settings_from_env_parses_nvme_devices(monkeypatch):
    monkeypatch.setenv("NVME_DEVICES", "/dev/nvme0n1, /dev/nvme1n1")

    settings = Settings.from_env()
    assert settings.nvme_devices == ["/dev/nvme0n1", "/dev/nvme1n1"]


def test_get_settings_is_cached(monkeypatch):
    monkeypatch.setenv("HA_BASE_URL", "http://example.local")
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
    assert s1.ha_base_url == "http://example.local"

def test_fritzbox_hosts_from_env(monkeypatch):
    monkeypatch.setenv("FRITZBOX_HOSTS", "fb1.local, fb2.local,fb3.local")
    from app.config import Settings
    settings = Settings.from_env()
    assert settings.fritzbox_hosts == ["fb1.local", "fb2.local", "fb3.local"]

