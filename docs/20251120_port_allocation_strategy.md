# Port Allocation Strategy for the Home Lab

**File:** `docs/20251120_port_allocation_strategy.md`  
**Scope:** Technical concept for consistent, conflict‑free port allocation across the home lab, including host services, Docker containers, reverse proxies, and monitoring components.

---

## 1. Goals and Design Principles

The purpose of this document is to define a **clear, repeatable port allocation strategy** for the entire home lab so that:

- New services can be added **without accidental port conflicts**.
- Port usage is **predictable and documented** across locations and hosts.
- Reverse proxies and monitoring tools can rely on a **stable, well-known port layout**.
- The existing `port_usage_report.py` tooling can be used to **validate** that the strategy is respected on any given host.

Design principles:

1. **Clarity over cleverness** – prefer simple, documented ranges and conventions over ad-hoc choices.
2. **Stable defaults** – once a port is assigned to a role (e.g. MQTT, Home Assistant), keep it stable.
3. **Layer separation** – distinguish between:
   - host system services
   - infrastructure / core lab services
   - application / project services
   - ephemeral / dynamic ports
4. **Docker-aware** – document both **host ports** and **container ports**, especially when using published ports (`host:port->container:port`) or `network_mode: host`.
5. **Multi-site capable** – the same conventions should work across multiple locations (e.g. home, remote site, lab node).

---

## 2. Port Categories and Ranges

We classify ports into several categories to keep the mental model simple.

### 2.1 System & OS-level services

Reserved for the OS, SSH and essential system daemons.

- Typical examples:
  - `22/tcp` – SSH
  - `53/tcp,udp` – DNS (if running locally)
  - `123/udp` – NTP (if running locally)
- **Policy:** Do not reuse these ports for applications or lab-level services.

### 2.2 Core Infrastructure Services

These ports are used for lab‑critical infrastructure, typically **one instance per host or per role**.

Examples (current convention / reality in the lab):

- `1883/tcp` – MQTT broker (e.g. Mosquitto, often in Docker, published on host)
- `5432/tcp` – PostgreSQL (local database)
- `3306/tcp` – MariaDB / MySQL (Nextcloud DB, other web apps)
- `6379/tcp` – Redis (Nextcloud cache, other components)

**Policy:**

- Infrastructure ports should be **standard / well-known** where possible (e.g. keep `1883` for MQTT).
- Only one service per well-known infrastructure port on a host.
- If multiple instances are required, use **namespaced ports** with clear documentation (e.g. `5433` for a second Postgres instance).

### 2.3 Reverse Proxy & Web Entry Points

Ports used by reverse proxies, gateways or public‑facing HTTP endpoints on the host.

Current and planned usage:

- `80/tcp` – HTTP (reverse proxy, often behind TLS terminator or redirect to HTTPS)
- `443/tcp` – HTTPS (reverse proxy / TLS termination)
- `8080/tcp` – Public/accessible lab web service (e.g. `jozapf_com_web`)
- `8081/tcp` – Public/accessible admin UI (e.g. phpMyAdmin)
- `8085/tcp` – Nextcloud nginx frontend (bound to `127.0.0.1` and `192.168.10.20`)

**Policy:**

- Treat `80` and `443` as **exclusive** for the primary reverse proxy on each host.
- Reserve the `8080–8099` range for **HTTP-based app frontends** that might be exposed:
  - `8080` – main lab web application / landing page
  - `8081` – web admin tools (e.g. DB admin)
  - `8085` – Nextcloud frontend (current usage)
- All of these must be documented and, where possible, fronted by reverse proxy vhosts / paths.

### 2.4 Application & Monitoring Services

Ports used by application-specific services, APIs and monitoring components (including this project).

Suggested convention:

- `8100–8199` – **Application APIs & microservices**
  - e.g. `8100` – Home Lab Infra Monitor (FastAPI app)
- `8200–8299` – **Background services / internal APIs** that are not meant to be directly user-facing, but may be called by other components.

**Policy:**

- Pick a **stable default** for each application (e.g. `8100` for this FastAPI service).
- If deployed via Docker, use:
  - container port: `8000` or `8100`
  - host port: follow the convention above and avoid overlap with reverse proxy (808x).

### 2.5 Ephemeral Ports

Ephemeral ports are used by the OS for outbound connections. They must never be assigned to services explicitly.

On Linux, the typical range is:

- `32768–60999` (can be confirmed via `/proc/sys/net/ipv4/ip_local_port_range`).

**Policy:**

- Do not bind services to ports within the ephemeral range unless there is a very good reason and it is documented.
- The `port_usage_report.py` script reads this range and includes it in its JSON output as `ip_local_port_range` for transparency.

---

## 3. Host vs Docker Port Mapping

The home lab uses Docker for many services. This introduces a split between:

- **Container ports** (inside Docker networks)
- **Host ports** (published to the host via `-p` / `ports:` in Compose)

### 3.1 Published Ports (`host:port->container:port`)

For containers with published ports, the mapping looks like this:

- Example:

  ```text
  0.0.0.0:1883->1883/tcp
  0.0.0.0:8080->80/tcp
  127.0.0.1:8085->8085/tcp, 192.168.10.20:8085->8085/tcp
  ```

**Strategy:**

- Always choose host ports according to the categories above (infra, web entry, app).
- Container ports can be **standard** (e.g. `80`, `1883`), but host ports are what matter in the global port allocation strategy.
- Use host IP binding intentionally:
  - `127.0.0.1:PORT` – internal only, to be consumed by local reverse proxy or services.
  - `0.0.0.0:PORT` – exposed on all interfaces (LAN/WAN depending on firewall).
  - `SITE_IP:PORT` – dedicated binding for a specific interface or subnet.

### 3.2 Host Network (`network_mode: "host"`)

Some containers (e.g. Home Assistant) may run with `network_mode: "host"`. In that case:

- The container **shares the host network stack**.
- Ports appear as **direct host listeners**, e.g. `0.0.0.0:8123` and `:: :8123` for Home Assistant.
- `docker ps` will not show a `Ports` mapping; it may show an empty `PORTS` column.

**Implications for this strategy:**

- Ports used by `network_mode: host` containers must be treated just like host processes.
- Allocation and documentation must ensure that these ports are reserved ahead of time (e.g. `8123` reserved for Home Assistant on the lab host).

---

## 4. Integration with `port_usage_report.py`

The `port_usage_report.py` helper is used to **validate** that the actual port usage on a host matches the conceptual strategy.

### 4.1 Data Collected

The script currently:

- Enumerates host listeners via `psutil.net_connections(kind="inet")` (only `LISTEN` state).
- Enriches data per port with:
  - `proto`, `ip`, `port`, `status`
  - `pid`, `user`, `process`, `cmdline` (where accessible)
- Integrates Docker information by parsing:

  ```bash
  docker ps --format '{{.Names}}	{{.ID}}	{{.Image}}	{{.Ports}}'
  ```

  and mapping host ports to:

  - `docker_container_name`
  - `docker_container_id`
  - `docker_image`
  - `docker_port_spec`
  - `docker_container_port`

- Includes metadata:
  - `host`
  - `generated_at`
  - `ip_local_port_range`
  - `docker` meta (`available`, counts, command)
  - `schema_version`, `script_version`

### 4.2 Use Cases

1. **Pre‑deployment check**  
   Before adding a new service or binding, run:

   ```bash
   cd docs
   ./port_usage_report.py --html
   ```

   - Inspect `port_usage_report.html` in a browser.
   - Verify that the planned host port is not already used or reserved.

2. **Runtime check for a specific port**  

   ```bash
   ./port_usage_report.py --check-port 8100
   ```

   - Exit code `0`: port is currently free.
   - Exit code `1`: port is in use or cannot be reliably checked.
   - This can be wired into deployment scripts or CI/CD jobs.

3. **Documentation snapshot**  
   - Store `port_usage_report.json` as a timestamped snapshot (e.g. `port_usage_report_<DATE>.json`) for historical reference.
   - Compare snapshots to track port usage evolution.

---

## 5. Recommended Port Assignments (Current Lab)

This section documents the **current and recommended** assignments for key services in the home lab. It is meant as a living list; updates should be made when services are added/removed.

> Note: Names and hostnames here are examples and should match the actual Docker Compose and host configuration.

### 5.1 Core Services

| Service / Role         | Host Port(s) | Proto | Notes                                      |
|------------------------|-------------:|:-----:|--------------------------------------------|
| SSH                    |          22  | tcp   | OS-level, do not reuse                     |
| MQTT (Mosquitto)       |        1883  | tcp   | `mosquitto` container, published on host   |
| PostgreSQL (if used)   |        5432  | tcp   | Local DB                                   |
| MariaDB / MySQL        |        3306  | tcp   | Nextcloud DB, generic DB                   |
| Redis                  |        6379  | tcp   | Nextcloud cache or other uses              |

### 5.2 Web & Reverse Proxy

| Service / Role           | Host Port(s)     | Proto | Example Container     | Notes                                           |
|--------------------------|-----------------:|:-----:|-----------------------|------------------------------------------------|
| Primary HTTP (reverse)   |               80 | tcp   | `nginx`, `caddy`, ... | Main entry, redirect to 443                    |
| Primary HTTPS (reverse)  |              443 | tcp   | `nginx`, `caddy`, ... | Main TLS termination                            |
| Main web app             |            8080  | tcp   | `jozapf_com_web`      | `0.0.0.0:8080->80/tcp`, externally reachable   |
| Admin / DB tools         |            8081  | tcp   | `jozapf_com_pma`      | `0.0.0.0:8081->80/tcp`, restricted access      |
| Nextcloud frontend       |            8085  | tcp   | `nextcloud-nginx`     | `127.0.0.1:8085` and `192.168.10.20:8085`      |

### 5.3 Application & Monitoring

| Service / Role                 | Host Port(s) | Proto | Notes                                              |
|--------------------------------|-------------:|:-----:|---------------------------------------------------|
| Home Lab Infra Monitor (API)   |        8100  | tcp   | Planned default FastAPI port                      |
| Internal APIs / jobs (generic) |   8200–8299  | tcp   | Reserved range for future internal services       |
| Home Assistant (host network)  |        8123  | tcp   | Uses host network, appears as direct host port    |

> When assigning new ports, always choose from the appropriate range and update this table accordingly.

---

## 6. Workflow for Adding New Services

To keep the port strategy consistent, follow this workflow whenever a new service is added.

1. **Classify the service**
   - Is it core infrastructure? reverse proxy frontend? app API? admin tool?
2. **Select the appropriate range**
   - Infra: use well-known port or a consciously chosen variant.
   - Web frontends: prefer `808x` range.
   - APIs / monitoring: prefer `8100–8299`.
3. **Check existing usage**
   - Run `./docs/port_usage_report.py --html`.
   - Inspect existing listeners on the planned host.
4. **Define Docker mapping (if containerized)**
   - Use a stable container port (e.g. `80`, `8000`, `8100`).
   - Map to a host port that follows the strategy (e.g. `0.0.0.0:8100->8100/tcp`).
5. **Update documentation**
   - Add or update the service in section **5. Recommended Port Assignments**.
   - Optionally keep timestamped JSON snapshots for audit/history.
6. **Re-run port report after deployment**
   - Confirm that the new listener appears as expected and does not conflict with other services.

---

## 7. Future Extensions

Possible future enhancements to this port allocation strategy and its tooling:

- **Central registry** of services and ports (YAML/JSON file in the repo) that can be validated against the live `port_usage_report.json`.
- **FastAPI endpoint** (e.g. `/host/ports`) exposing a filtered, read-only view of active ports to the monitoring UI.
- **CI checks** that compare planned ports vs. ports in use on a reference host or test environment.
- **Per-site profiles** (if multiple sites use different ranges or roles, e.g. core, edge, DMZ).

Until then, this document and the `port_usage_report.py` helper form the basis for **manual but structured** port management in the home lab.
