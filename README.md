![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-async%20API-brightgreen)
[![CI](https://github.com/JoZapf/home-lab-infra-monitor/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/JoZapf/home-lab-infra-monitor/actions/workflows/ci.yml)
![Status](https://img.shields.io/badge/status-WIP-orange)

# Home Lab Infra Monitor
> ⚠️ **Work in progress:** APIs, services and docs are actively evolving. 
---
> Home Lab Infra Monitor is a FastAPI-based service for monitoring a distributed home lab via typed services and centralized, environment-based configuration. :contentReference[oaicite:0]{index=0}

<p align="center">
  <img src="docs/architecture_multi-site_hardware-network_infra-monitor.svg" alt="Architecture Overview">
</p>

> 🔌 **Port usage reporting (host & Docker ports):** experimental offline tooling is available, see [Port Usage Reporting (host & Docker ports)](#port-usage-reporting-host--docker-ports).

## Table of Contents

1. [Overview](#overview)
2. [Current Architecture](#current-architecture)
3. [Configuration](#configuration)
4. [Implemented Features](#implemented-features)
5. [Planned Features](#planned-features)
6. [Development & Testing](#development--testing)
7. [Folder Structure (planned)](#folder-structure-planned)
8. [Port Usage Reporting (host & Docker ports)](#port-usage-reporting-host--docker-ports)

---

## Overview

- Goal: unified monitoring layer for a multi-site home lab (3 locations).
- Focus: host, NVMe storage, routers and Home Assistant, exposed via a small FastAPI service.
- Design: strict layering (API → services → models) and env-driven configuration.

---

## Current Architecture

- **API layer**
  - `/health/` – basic health check.
  - `/host/status` – typed host status (hostname, uptime, CPU, RAM, disk).
  - `/nvme/status` – NVMe device temperatures and critical flag.
  - `/fritz/status` – reachability and latency for configured routers/FritzBox hosts.

- **Service layer**
  - `HostMonitor` (`app.services.host_monitor.get_host_status`) collects system metrics via `psutil`, `socket`, `time`.
  - `NvmeMonitor` (`app.services.nvme_monitor.get_nvme_status`) reads configured NVMe devices and smart-log data.
  - `FritzMonitor` (`app.services.fritz_monitor.get_fritz_status`) checks reachability/latency for hosts from `FRITZBOX_HOSTS`.

- **Domain models**
  - `HostStatus` (`app.models.host.HostStatus`) as a Pydantic model with validated fields and OpenAPI integration.

- **Config layer**
  - `Settings` (`app.config.Settings`) reads environment variables (HA, routers, NVMe) into a typed object.
  - `get_settings()` (cached) as the single entry point for configuration in services.

- **Docs**
  - Runbooks and PlantUML diagrams in `docs/` describe architecture, flows and host/config layers.

---

## Configuration

Configuration is driven entirely via environment variables,... typically provided through a local `.env` file (not committed).

Key variables (see `.env.example`):

- `HA_BASE_URL` – base URL of the Home Assistant instance (NUC).
- `HA_TOKEN` – optional long-lived access token.
- `FRITZBOX_HOSTS` – comma-separated list of router/FritzBox hosts.
- `FRITZBOX_USERNAME`, `FRITZBOX_PASSWORD` – shared credentials (optional).
- `NVME_DEVICES` – comma-separated list of NVMe devices (e.g. `/dev/nvme0n1,/dev/nvme1n1`).

Docker:

- `docker-compose.yml` loads `.env` via `env_file: .env` into the container environment.

---

## Implemented Features

- **FastAPI app**
  - Health endpoint `/health/`.
  - Host endpoint `/host/status` with clean layering (API → service → model).
  - NVMe endpoint `/nvme/status` for temperature/critical state of configured NVMe devices.
  - FritzBox endpoint `/fritz/status` for reachability and latency per configured host.

- **Domain / service separation**
  - `HostStatus` model for host metrics.
  - `NvmeDeviceStatus` model for NVMe device temperature/critical state.
  - `FritzHostStatus` model for router/FritzBox reachability and latency.
  - `host_monitor` service encapsulating system access.
  - `nvme_monitor` service reading smart-log via nvme-cli for configured devices.
  - `fritz_monitor` service handling ping-based reachability/latency checks.

- **Configuration layer**
  - `app/config.py` with `Settings` + `get_settings()` (multi-router, NVMe devices, HA URL).
  - `.env.example` as documented template.
  - `.env` excluded via `.gitignore`.

- **Tests & CI**
  - `tests/test_health.py`, `tests/test_host.py`, `tests/test_nvme.py`, `tests/test_fritz.py`, `tests/test_config.py`.
  - GitHub Actions workflow (`ci.yml`) runs `pytest` on push/PR to `main`.

---

## Planned Features

- **NVMe monitoring enhancements**
  - Extend existing `NvmeDeviceStatus`/`nvme_monitor` with capacity, usage and wear-level/health information.
  - Add further tests for value ranges and plausibility of extended metrics.

- **Router/FritzBox monitoring enhancements**
  - Extend existing ping-based `/fritz/status` with WAN status and additional router/FritzBox metrics.
  - Optionally integrate HTTP/TR-064 APIs for DSL/link statistics and connected clients.
  - Add more detailed tests (e.g. for WAN status aggregation and API error handling).

- **Home Assistant integration**
  - Service for basic HA status (reachability, version, core state).
  - Auth via `HA_TOKEN`.
  - `/ha/status` endpoint.
  - Tests with stubbed HTTP requests.

- **Further steps**
  - More service-level tests, error paths and edge cases.
  - Optional: Prometheus metrics, UI/frontend, alerting.

---

## Development & Testing

```bash
# activate venv
source .venv/bin/activate

# run FastAPI app (dev)
uvicorn app.main:app --reload

# run tests
pytest

```


## Folder Structure
```
home-lab-infra-monitor/
├─ app/
│ ├─ init.py
│ ├─ main.py # FastAPI app & router registration
│ ├─ config.py # Settings + get_settings()
│ ├─ api/
│ │ ├─ init.py
│ │ ├─ health.py # /health/
│ │ ├─ host.py # /host/status
│ │ ├─ nvme.py # /nvme/status
│ │ ├─ fritz.py # /fritz/status
│ │ └─ home_assistant.py # (planned) /ha/status
│ ├─ services/
│ │ ├─ host_monitor.py # host metrics (psutil, socket, time)
│ │ ├─ nvme_monitor.py # nvme smart-log + error handling
│ │ ├─ fritz_monitor.py # ping-based reachability/latency
│ │ └─ ha_monitor.py # (planned) HA status
│ └─ models/
│ ├─ host.py # HostStatus
│ ├─ nvme.py # NvmeDeviceStatus
│ ├─ fritz.py # FritzHostStatus
│ └─ home_assistant.py # (planned)
├─ tests/
│ ├─ test_health.py
│ ├─ test_host.py
│ ├─ test_nvme.py
│ ├─ test_fritz.py
│ └─ test_config.py
├─ docs/ # Runbooks, PlantUML diagrams, architecture notes
├─ .github/
│ └─ workflows/
│ └─ ci.yml # CI pipeline (pytest)
├─ .env.example
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt or pyproject.toml
└─ README.md
```
