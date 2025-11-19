from pydantic import BaseModel, Field


class HostStatus(BaseModel):
    """Domain model describing the current host status."""

    hostname: str = Field(..., description="System hostname")
    uptime_seconds: int = Field(
        ...,
        ge=0,
        description="Number of seconds since the system was booted",
    )
    cpu_load_percent: float = Field(
        ...,
        ge=0,
        le=100,
        description="CPU utilisation in percent over a short sampling interval",
    )
    memory_used_percent: float = Field(
        ...,
        ge=0,
        le=100,
        description="RAM usage in percent",
    )
    disk_used_percent: float = Field(
        ...,
        ge=0,
        le=100,
        description="Root filesystem usage in percent",
    )

