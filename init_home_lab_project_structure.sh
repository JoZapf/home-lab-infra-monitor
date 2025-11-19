#!/usr/bin/env bash
set -euo pipefail

# Projektname als optionales Argument, Standard: home-lab-infra-monitor
PROJECT_ROOT="${1:-home-lab-infra-monitor}"

echo "Erstelle Projektstruktur unter: ${PROJECT_ROOT}"

# Verzeichnisse anlegen
mkdir -p "${PROJECT_ROOT}/app/api"
mkdir -p "${PROJECT_ROOT}/app/services"
mkdir -p "${PROJECT_ROOT}/app/models"
mkdir -p "${PROJECT_ROOT}/tests"

# Python-Pakete/Module
touch "${PROJECT_ROOT}/app/__init__.py"
touch "${PROJECT_ROOT}/app/main.py"

touch "${PROJECT_ROOT}/app/api/__init__.py"
touch "${PROJECT_ROOT}/app/api/health.py"
touch "${PROJECT_ROOT}/app/api/host.py"
touch "${PROJECT_ROOT}/app/api/nvme.py"
touch "${PROJECT_ROOT}/app/api/fritz.py"
touch "${PROJECT_ROOT}/app/api/home_assistant.py"

touch "${PROJECT_ROOT}/app/services/host_monitor.py"
touch "${PROJECT_ROOT}/app/services/nvme_monitor.py"
touch "${PROJECT_ROOT}/app/services/fritz_monitor.py"
touch "${PROJECT_ROOT}/app/services/ha_monitor.py"

touch "${PROJECT_ROOT}/app/models/host.py"
touch "${PROJECT_ROOT}/app/models/nvme.py"
touch "${PROJECT_ROOT}/app/models/fritz.py"
touch "${PROJECT_ROOT}/app/models/home_assistant.py"

# Sonstige Dateien im Projekt-Root
touch "${PROJECT_ROOT}/tests/__init__.py"  # optional, kann auch leer bleiben oder entfallen

touch "${PROJECT_ROOT}/requirements.txt"
touch "${PROJECT_ROOT}/Dockerfile"
touch "${PROJECT_ROOT}/docker-compose.yml"
touch "${PROJECT_ROOT}/README.md"

echo "Fertig. Struktur angelegt in: ${PROJECT_ROOT}"

