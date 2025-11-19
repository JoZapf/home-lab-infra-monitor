from fastapi import FastAPI

from .api import health, host, nvme, fritz

app = FastAPI(title="Home Lab Infra Monitor")

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(host.router, prefix="/host", tags=["host"])
app.include_router(nvme.router, prefix="/nvme", tags=["nvme"])
app.include_router(fritz.router, prefix="/fritz", tags=["fritz"])

