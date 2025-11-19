from pydantic import BaseModel, Field


class NvmeDeviceStatus(BaseModel):
    """Domain model describing the status of a single NVMe device."""

    device: str = Field(
        ...,
        description="Device path, e.g. /dev/nvme0n1",
    )
    temperature_celsius: float = Field(
        ...,
        ge=-20.0,
        le=130.0,
        description="Current NVMe temperature in degrees Celsius",
    )
    is_critical: bool = Field(
        ...,
        description="True if temperature is at or above the warning threshold.",
    )

