from typing import List, Optional
from pydantic import BaseModel, Field
import os
from functools import lru_cache

# ... (HA + NVMe bleiben wie vorher)

class Settings(BaseModel):
    # Home Assistant (wie gehabt)
    ha_base_url: Optional[str] = Field(
        default=None,
        description="Base URL of the Home Assistant instance, e.g. http://ha-nuc:8123",
    )
    ha_token: Optional[str] = Field(
        default=None,
        description="Long-lived access token for Home Assistant (optional for now)",
    )

    # Fritz!Box: mehrere Hosts, gemeinsame Credentials
    fritzbox_hosts: Optional[List[str]] = Field(
        default=None,
        description="List of Fritz!Box hosts or IPs to monitor",
    )
    fritzbox_username: Optional[str] = Field(
        default=None,
        description="Username for Fritz!Box API/login",
    )
    fritzbox_password: Optional[str] = Field(
        default=None,
        description="Password for Fritz!Box API/login",
    )

    # NVMe / storage (wie gehabt)
    nvme_devices: Optional[List[str]] = Field(
        default=None,
        description="Optional list of NVMe device paths, e.g. ['/dev/nvme0n1']",
    )

    @classmethod
    def from_env(cls) -> "Settings":
        # NVMe-Parsing (wie vorher)
        raw_nvme = os.getenv("NVME_DEVICES", "")
        nvme_devices = [item.strip() for item in raw_nvme.split(",") if item.strip()] or None

        # FritzBox-Hosts: neue Variable FRITZBOX_HOSTS, Fallback auf altes FRITZBOX_HOST
        raw_fritz_hosts = os.getenv("FRITZBOX_HOSTS") or os.getenv("FRITZBOX_HOST", "")
        fritzbox_hosts = [h.strip() for h in raw_fritz_hosts.split(",") if h.strip()] or None

        return cls(
            ha_base_url=os.getenv("HA_BASE_URL"),
            ha_token=os.getenv("HA_TOKEN"),
            fritzbox_hosts=fritzbox_hosts,
            fritzbox_username=os.getenv("FRITZBOX_USERNAME"),
            fritzbox_password=os.getenv("FRITZBOX_PASSWORD"),
            nvme_devices=nvme_devices,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()

