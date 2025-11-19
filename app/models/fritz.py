from typing import Optional

from pydantic import BaseModel, Field


class FritzHostStatus(BaseModel):
    """Status of a single FritzBox host (reachability and latency)."""

    host: str = Field(
        ...,
        description="Hostname or IP of the FritzBox, e.g. fritz.box or 192.168.178.1",
    )
    is_up: bool = Field(
        ...,
        description="True if the host responded to a ping probe.",
    )
    latency_ms: Optional[float] = Field(
        None,
        ge=0.0,
        description="Roundtrip time in milliseconds, if measurable.",
    )
    error: Optional[str] = Field(
        None,
        description="Optional error message if the host is not reachable or the probe failed.",
    )

