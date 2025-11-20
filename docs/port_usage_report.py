#!/usr/bin/env python3
"""
port_usage_report.py

Version: 1.1.1

Changelog:
- 1.0.0: Initial version, JSON report + optional HTML view +
         runtime TCP port check.
- 1.1.0: Docker integration. Annotates ports that belong to Docker containers
         using:
         docker ps --format 'table {{.Names}}\t{{.ID}}\t{{.Image}}\t{{.Ports}}'
- 1.1.1: Documentation and validation of the Docker port mapping logic based on
         the existing container landscape (including nextcloud-nginx, mosquitto);
         no functional changes to the report format.

Credits:
- learning project "Home Lab Infra Monitor".
- Author: Jo Zapf (Homelab / Infra / Monitoring).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import socket
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil

__version__ = "1.1.0"


def get_script_paths() -> Tuple[Path, str]:
    """
    Liefert (script_dir, script_stem).
    script_stem = Dateiname ohne Endung, z. B. 'port_usage_report'.
    """
    script_path = Path(__file__).resolve()
    script_dir = script_path.parent
    return script_dir, script_path.stem


def get_ip_local_port_range() -> Optional[Tuple[int, int]]:
    """
    Versucht, die lokale Ephemeral-Port-Range unter Linux zu lesen.
    Unter anderen Systemen wird None zurückgegeben.
    """
    path = Path("/proc/sys/net/ipv4/ip_local_port_range")
    if not path.exists():
        return None
    try:
        content = path.read_text(encoding="utf-8").strip()
        low_str, high_str = content.split()
        return int(low_str), int(high_str)
    except Exception:
        return None


def collect_docker_port_mappings() -> Tuple[
    Dict[Tuple[str, str, int], Dict[str, Any]], Dict[str, Any]
]:
    """
    Liest Docker-Container und deren veröffentlichte Ports ein.

    Nutzt den Befehl:
        docker ps --format '{{.Names}}\\t{{.ID}}\\t{{.Image}}\\t{{.Ports}}'

    Rückgabe:
        - mapping: Key = (proto, host_ip, host_port)
        - meta:    Meta-Informationen zur Docker-Integration
    """
    cmd = [
        "docker",
        "ps",
        "--format",
        "{{.Names}}\t{{.ID}}\t{{.Image}}\t{{.Ports}}",
    ]
    mapping: Dict[Tuple[str, str, int], Dict[str, Any]] = {}
    meta: Dict[str, Any] = {
        "available": False,
        "error": None,
        "containers_total": 0,
        "containers_with_published_ports": 0,
        "command": "docker ps --format '{{.Names}}\\t{{.ID}}\\t{{.Image}}\\t{{.Ports}}'",
    }

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        meta["error"] = "docker binary not found"
        return mapping, meta
    except subprocess.CalledProcessError as e:
        meta["error"] = f"docker ps failed: {e}"
        return mapping, meta

    output = result.stdout.strip()
    if not output:
        meta["available"] = True
        return mapping, meta

    lines = output.splitlines()
    if not lines:
        meta["available"] = True
        return mapping, meta

    containers_total = 0
    containers_with_published_ports: set[str] = set()

    for line in lines:
        if not line.strip():
            continue

        # Spalten sind per Tab getrennt (Names, ID, Image, Ports)
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < 4:
            continue

        name, cid, image, ports_str = parts[0], parts[1], parts[2], parts[3]
        containers_total += 1

        if not ports_str:
            continue

        has_published = False

        # Beispiel: "0.0.0.0:8080->80/tcp, [::]:8080->80/tcp"
        for entry in [e.strip() for e in ports_str.split(",") if e.strip()]:
            # Nur host->container-Mappings wie "IP:port->port/proto"
            if "->" not in entry:
                continue

            left, right = entry.split("->", 1)
            left = left.strip()
            right = right.strip()

            # right: "<container_port>/<proto>"
            if "/" in right:
                container_port_str, proto = right.split("/", 1)
            else:
                container_port_str, proto = right, ""
            proto = proto.lower().strip() or "tcp"

            # left: "<host_ip>:<host_port>", z. B. "0.0.0.0:8080" oder "[::]:8081"
            if ":" not in left:
                continue
            host_ip_raw, host_port_str = left.rsplit(":", 1)
            host_ip = host_ip_raw.strip()
            if host_ip.startswith("[") and host_ip.endswith("]"):
                host_ip = host_ip[1:-1]

            try:
                host_port = int(host_port_str)
            except ValueError:
                continue

            try:
                container_port = int(container_port_str)
            except ValueError:
                container_port = container_port_str  # Fallback: Rohstring

            key = (proto, host_ip, host_port)
            mapping[key] = {
                "container_name": name,
                "container_id": cid,
                "image": image,
                "port_spec": entry,
                "container_port": container_port,
            }
            has_published = True

        if has_published:
            containers_with_published_ports.add(name)

    meta["available"] = True
    meta["containers_total"] = containers_total
    meta["containers_with_published_ports"] = len(containers_with_published_ports)
    return mapping, meta



def collect_port_usage(
    docker_map: Optional[Dict[Tuple[str, str, int], Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Liefert eine sortierte Liste von Ports (nur Listener),
    inkl. Protokoll, IP, Port, Status, PID, Benutzer, Prozessname, Cmdline
    und – falls vorhanden – Docker-Informationen.
    """
    records: List[Dict[str, Any]] = []
    docker_map = docker_map or {}

    # inet = TCP + UDP (IPv4/IPv6)
    connections = psutil.net_connections(kind="inet")

    for conn in connections:
        # Wir interessieren uns hier primär für Listener (Port-Konflikte)
        if conn.status != psutil.CONN_LISTEN:
            continue

        laddr = conn.laddr
        ip = getattr(laddr, "ip", None)
        port = getattr(laddr, "port", None)

        if ip is None or port is None:
            continue

        if conn.type == socket.SOCK_STREAM:
            proto = "tcp"
        elif conn.type == socket.SOCK_DGRAM:
            proto = "udp"
        else:
            proto = "other"

        pid = conn.pid
        process_name: Optional[str] = None
        cmdline: Optional[str] = None
        username: Optional[str] = None

        if pid:
            try:
                p = psutil.Process(pid)
                process_name = p.name()
                cmdline = " ".join(p.cmdline())
                username = p.username()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        record: Dict[str, Any] = {
            "proto": proto,
            "ip": ip,
            "port": int(port),
            "status": conn.status,  # i. d. R. 'LISTEN'
            "pid": pid,
            "user": username,
            "process": process_name,
            "cmdline": cmdline,
        }

        # Docker-Integration: Host-Port/Proto/IP mit Docker-Mapping verknüpfen
        key = (proto, ip, int(port))
        docker_info = docker_map.get(key)
        if docker_info:
            record["docker_container_name"] = docker_info.get("container_name")
            record["docker_container_id"] = docker_info.get("container_id")
            record["docker_image"] = docker_info.get("image")
            record["docker_port_spec"] = docker_info.get("port_spec")
            record["docker_container_port"] = docker_info.get("container_port")

        records.append(record)

    # Sortierung: Protokoll, Port, IP
    records.sort(key=lambda r: (r["proto"], r["port"], r["ip"]))
    return records


def build_report() -> Dict[str, Any]:
    """
    Baut das JSON-Report-Objekt.
    """
    hostname = socket.gethostname()
    generated_at = dt.datetime.now(dt.timezone.utc).isoformat()

    docker_map, docker_meta = collect_docker_port_mappings()
    records = collect_port_usage(docker_map)
    ip_range = get_ip_local_port_range()

    report: Dict[str, Any] = {
        "schema_version": "1.1.0",
        "script_version": __version__,
        "host": hostname,
        "generated_at": generated_at,
        "ip_local_port_range": {
            "low": ip_range[0],
            "high": ip_range[1],
        }
        if ip_range
        else None,
        "docker": docker_meta,
        "ports": records,
    }
    return report


def write_json_report(report: Dict[str, Any], output_path: Path) -> None:
    """
    Schreibt den Report als JSON-Datei.
    """
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def generate_html_report(report: Dict[str, Any], output_path: Path) -> None:
    """
    Erzeugt eine einfache HTML-Ansicht des Reports für menschliche Leser.
    Anzeige in einem Browser (lokales File) möglich.
    """
    # JSON als JS-Objekt einbetten
    json_data = json.dumps(report, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <title>Port Usage Report – {report.get("host", "")}</title>
    <style>
        body {{
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            margin: 1.5rem;
            background: #f5f5f5;
        }}
        h1, h2 {{
            margin-bottom: 0.25rem;
        }}
        .meta {{
            margin-bottom: 1rem;
            font-size: 0.9rem;
            color: #555;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            background: #fff;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 0.35rem 0.5rem;
            font-size: 0.8rem;
        }}
        th {{
            background: #eee;
            position: sticky;
            top: 0;
            z-index: 1;
        }}
        tr:nth-child(even) td {{
            background: #fafafa;
        }}
        code {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        }}
        .status {{
            text-transform: lowercase;
        }}
    </style>
</head>
<body>
    <h1>Port Usage Report</h1>
    <div class="meta">
        <div><strong>Host:</strong> <code id="meta-host"></code></div>
        <div><strong>Erzeugt am:</strong> <span id="meta-generated"></span></div>
        <div><strong>Script-Version:</strong> <span id="meta-version"></span></div>
        <div><strong>Anzahl Ports (LISTEN):</strong> <span id="meta-count"></span></div>
        <div><strong>Ephemeral-Range (falls ermittelt):</strong> <span id="meta-range"></span></div>
        <div><strong>Docker-Integration:</strong> <span id="meta-docker"></span></div>
    </div>

    <h2>Ports</h2>
    <table id="ports-table">
        <thead>
            <tr>
                <th>Proto</th>
                <th>IP</th>
                <th>Port</th>
                <th>Status</th>
                <th>PID</th>
                <th>User</th>
                <th>Process</th>
                <th>Cmdline</th>
                <th>Docker Name</th>
                <th>Docker ID</th>
                <th>Docker Image</th>
                <th>Docker Mapping</th>
            </tr>
        </thead>
        <tbody></tbody>
    </table>

    <script>
        const report = {json_data};

        function renderReport() {{
            const host = report.host || "";
            const generated = report.generated_at || "";
            const ports = Array.isArray(report.ports) ? report.ports : [];
            const version = report.script_version || "";

            const range = report.ip_local_port_range;
            const rangeText = range && typeof range.low === "number" && typeof range.high === "number"
                ? range.low + " - " + range.high
                : "unbekannt";

            const docker = report.docker || {{}};
            const dockerAvailable = docker.available === true;
            const dockerText = dockerAvailable
                ? "aktiv (Container gesamt: " + (docker.containers_total || 0) +
                  ", mit veröffentlichten Ports: " + (docker.containers_with_published_ports || 0) + ")"
                : (docker.error ? "inaktiv – " + docker.error : "inaktiv");

            document.getElementById("meta-host").textContent = host;
            document.getElementById("meta-generated").textContent = generated;
            document.getElementById("meta-count").textContent = String(ports.length);
            document.getElementById("meta-range").textContent = rangeText;
            document.getElementById("meta-version").textContent = version;
            document.getElementById("meta-docker").textContent = dockerText;

            const tbody = document.querySelector("#ports-table tbody");
            tbody.innerHTML = "";

            for (const p of ports) {{
                const tr = document.createElement("tr");

                const cells = [
                    p.proto || "",
                    p.ip || "",
                    p.port != null ? String(p.port) : "",
                    p.status || "",
                    p.pid != null ? String(p.pid) : "",
                    p.user || "",
                    p.process || "",
                    p.cmdline || "",
                    p.docker_container_name || "",
                    p.docker_container_id || "",
                    p.docker_image || "",
                    p.docker_port_spec || "",
                ];

                cells.forEach((value, idx) => {{
                    const td = document.createElement("td");
                    if (idx === 3) {{
                        td.className = "status";
                    }}
                    if (idx === 0 || idx === 1 || idx === 2 || idx === 4 || idx === 9) {{
                        const code = document.createElement("code");
                        code.textContent = value;
                        td.appendChild(code);
                    }} else {{
                        td.textContent = value;
                    }}
                    tr.appendChild(td);
                }});

                tbody.appendChild(tr);
            }}
        }}

        document.addEventListener("DOMContentLoaded", renderReport);
    </script>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")



def check_port_free(host: str, port: int, timeout: float = 0.5) -> bool:
    """
    Prüft, ob ein TCP-Port auf einem Host frei ist.

    Rückgabe:
        True  -> Port ist frei (kein Listener)
        False -> Port ist belegt oder nicht eindeutig prüfbar
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            result = s.connect_ex((host, port))
        except OSError:
            # Konservative Interpretation: nicht frei / nicht erreichbar
            return False
        return result != 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Erzeugt einen JSON-Port-Usage-Report und optional eine HTML-Ansicht.\n"
            "Optional kann ein Port zur Laufzeit auf freie Belegbarkeit geprüft werden."
        )
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host/IP für den Laufzeit-Port-Check (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--check-port",
        type=int,
        help=(
            "Optional: TCP-Port für Laufzeit-Check. "
            "Exit-Code 0 = frei, 1 = belegt/Fehler."
        ),
    )
    parser.add_argument(
        "--json-path",
        type=str,
        help=(
            "Optional: Pfad für JSON-Output. "
            "Default: port_usage_report.json im Skriptverzeichnis."
        ),
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Erzeugt zusätzlich eine HTML-Ansicht (port_usage_report.html).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_dir, stem = get_script_paths()

    json_path = Path(args.json_path) if args.json_path else script_dir / f"{stem}.json"
    html_path = script_dir / f"{stem}.html"

    # Offline-Report (fix): JSON erzeugen
    report = build_report()
    write_json_report(report, json_path)
    print(f"[INFO] JSON-Report geschrieben nach: {json_path}")

    # Optional: menschenoptimierte HTML-Ansicht erzeugen
    if args.html:
        generate_html_report(report, html_path)
        print(f"[INFO] HTML-Report geschrieben nach: {html_path}")

    # Optional: Laufzeit-Port-Check
    if args.check_port is not None:
        port = args.check_port
        host = args.host
        is_free = check_port_free(host, port)
        if is_free:
            print(f"[OK] Port {port} auf {host} ist frei.")
            return 0
        else:
            print(
                f"[ERROR] Port {port} auf {host} ist belegt oder nicht eindeutig prüfbar."
            )
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

