# Intermediate Status – Home Lab Infra Monitor  
**Date/Time:** 2025-11-20, 14:00  

This document captures the current technical intermediate status of the **Home Lab Infra Monitor** project. It serves as a snapshot for architecture, implementation, and planning decisions.

---

## 1. Implemented Features

### 1.1 FastAPI Endpoints

✅ **Currently implemented HTTP endpoints:**

- `GET /health/`  
  - Simple health check (service liveness).
- `GET /host/status`  
  - Host metrics: hostname, uptime, CPU usage, RAM, disk.
- `GET /nvme/status`  
  - NVMe devices: temperature and critical/health flags for configured devices.
- `GET /fritz/status`  
  - Router/FritzBox reachability and latency for configured hosts.

---

### 1.2 Service Layer

✅ **Service layer is clearly separated from the API layer:**

- **`HostMonitor`**
  - Reads system metrics via `psutil`, `socket`, `time`.
  - Provides structured data for the host endpoint.
- **`NvmeMonitor`**
  - Reads smart-log data of configured NVMe devices (temperatures, flags).
- **`FritzMonitor`**
  - Performs ping-based reachability and latency checks for configured routers/FritzBox devices.

---

### 1.3 Domain Models

✅ **Pydantic data models defined:**

- `HostStatus` – typed representation of host metrics.
- `NvmeDeviceStatus` – status model for NVMe (temperature & critical flags).
- `FritzHostStatus` – model for router/FritzBox reachability and latency.

These models are automatically documented in the OpenAPI schema by FastAPI.

---

### 1.4 Configuration

✅ **Central, typed configuration layer:**

- `Settings` class (e.g. `app.config.Settings`) encapsulates all relevant environment variables (NVMe, routers/FritzBox, Home Assistant, etc.).  
- `get_settings()` with caching (e.g. `lru_cache`) acts as the single entry point for configuration in the service layer.
- `.env.example` serves as a **template** for productive `.env` files and documents all required variables.

---

### 1.5 Testing & CI

✅ **Test coverage & CI pipeline:**

- Unit tests for all relevant endpoints and configuration:
  - `/health/`
  - `/host/status`
  - `/nvme/status`
  - `/fritz/status`
  - Config/Settings tests
- GitHub Actions CI workflow (`.github/workflows/ci.yml`):
  - Runs `pytest` on every push/PR to `main`.
  - Serves as a foundation for further quality and integration checks.

---

### 1.6 Port Usage Reporting (experimental)

✅ **Experimental standalone tool for port analysis:**

- **Script:** `docs/port_usage_report.py`
- **Functionality:**
  - Collects host ports in `LISTEN` state via `psutil.net_connections(kind="inet")`.
  - Reads and parses `docker ps --format '{{.Names}}\t{{.ID}}\t{{.Image}}\t{{.Ports}}'` to integrate *published* Docker ports.
  - Links host ports with Docker metadata (container name, ID, image, mapping).
- **Outputs:**
  - **JSON report:** `docs/port_usage_report.json` (canonical format, including metadata such as host, timestamp, ephemeral port range, Docker status).
  - **Optional HTML:** `docs/port_usage_report.html` – for a human-friendly overview in the browser.
- **Status:**  
  - Not yet integrated into the FastAPI app or CI pipeline.  
  - Currently used offline to detect potential port conflicts before new deployments.

---

## 2. Next Steps (Planned Features)

### 2.1 Short-Term Extensions

#### 2.1.1 Extend NVMe Monitoring

🔧 Planned extensions:

- Add:
  - Capacity (total/used/free),
  - Utilization,
  - Wear-level/health information (as far as available via smart-log).
- Additional tests:
  - Range checks (sanity),
  - Plausibility checks (e.g. temperature ranges, wear-level bounds).

---

#### 2.1.2 Extend Router/FritzBox Monitoring

🔧 Planned extensions:

- WAN status (online/offline, link status, possibly reconnect counters).
- Additional per-router/FritzBox metrics (e.g. signal quality, sync rate – depending on API availability).
- Optionally integrate HTTP/TR-064 APIs for:
  - DSL/link statistics,
  - connected clients,
  - potentially traffic statistics.

- Planned tests:
  - Structured tests for WAN status aggregation,
  - API error handling (timeouts, auth errors, incomplete data).

---

#### 2.1.3 Home Assistant Integration

🔧 Planned integration:

- New service (e.g. `ha_monitor`):
  - Determines reachability of the HA backend.
  - Fetches basic information (version, core state, possibly last restart time).
- Authentication:
  - Via `HA_TOKEN` (Home Assistant long-lived access token).
- New endpoint:
  - `GET /ha/status` – typed status endpoint for Home Assistant.
- Tests:
  - Mocked HTTP requests (no need to hit a real HA instance).
  - Verification of error handling (401/403, network failures).

---

#### 2.1.4 Port Usage Report Integration

🔧 Planned integration into the overall service:

- Optional FastAPI endpoint:
  - `GET /host/ports` – consumes the logic from `port_usage_report.py` (or a factored-out library) and returns a filtered JSON view.
- CI checks for port conflicts:
  - Use `port_usage_report.py` (or its library variant) to check for conflicts on predefined ports prior to deployments.
- Extended documentation:
  - Already started: `docs/20251120_port_allocation_strategy.md` as technical foundation.
  - Further examples and best practices for port planning in the home lab.

---

### 2.2 Mid-Term Extensions

🔄 **More service-level tests, error paths, and edge cases**  
- Systematic coverage of failure scenarios in all services (e.g. missing devices, network errors, invalid configuration).  
- Goal: more robust services and clearer error reporting for frontend/monitoring consumers.

🔄 **Prometheus metrics (optional)**  
- Export of key metrics as Prometheus-compatible metrics (e.g. via `/metrics` endpoint or dedicated exporter).  
- Integration into existing monitoring stacks (Prometheus, Grafana).

🔄 **UI/Frontend (optional)**  
- A lightweight web UI for consolidated dashboards (host, NVMe, FritzBox, HA, ports).  
- Consumption of the FastAPI JSON APIs.

🔄 **Alerting (optional)**  
- Integration with existing alerting systems (e.g. Grafana alerts, Apprise, Home Assistant automations).  
- Definition of thresholds (temperatures, latencies, uptime requirements).

---

## 3. Summary

As of 2025-11-20, 14:00, the project provides a **solid foundation** with clearly separated layers (API, services, domain models, configuration, tests) and an experimental but already practically useful **Port Usage Reporting** tool.  
The next steps focus on **richer metrics (NVMe, routers, HA)**, **port strategy integration**, and, in the mid term, **monitoring/alerting integration**.
