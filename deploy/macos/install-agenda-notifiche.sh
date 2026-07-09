#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON="${ROOT}/.venv/bin/python"
PLIST_SRC="${ROOT}/deploy/macos/com.securtek.agenda-notifiche.plist"
PLIST_DST="${HOME}/Library/LaunchAgents/com.securtek.agenda-notifiche.plist"
LOG_DIR="${ROOT}/logs"
DOMAIN="gui/$(id -u)"

if [[ ! -x "${PYTHON}" ]]; then
    echo "Python virtuale non trovato: ${PYTHON}" >&2
    exit 1
fi

mkdir -p "${LOG_DIR}"

sed \
    -e "s|__PROJECT_ROOT__|${ROOT}|g" \
    -e "s|__PYTHON__|${PYTHON}|g" \
    "${PLIST_SRC}" > "${PLIST_DST}"

launchctl bootout "${DOMAIN}/com.securtek.agenda-notifiche" 2>/dev/null || true
launchctl bootstrap "${DOMAIN}" "${PLIST_DST}"
launchctl enable "${DOMAIN}/com.securtek.agenda-notifiche"

echo "Job installato: ${PLIST_DST}"
echo "Esecuzione programmata ogni giorno alle 08:00"
echo "Log: ${LOG_DIR}/agenda-notifiche.log"
