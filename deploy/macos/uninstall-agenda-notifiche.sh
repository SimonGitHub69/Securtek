#!/bin/bash
# Rimuove il servizio launchd delle notifiche agenda (Agent e/o Daemon).
set -euo pipefail

LABEL="com.securtek.agenda-notifiche"
AGENT_PLIST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
DAEMON_PLIST="/Library/LaunchDaemons/${LABEL}.plist"

REMOVED=0

if [[ -f "${AGENT_PLIST}" ]]; then
    launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
    rm -f "${AGENT_PLIST}"
    echo "Rimosso LaunchAgent: ${AGENT_PLIST}"
    REMOVED=1
fi

if [[ -f "${DAEMON_PLIST}" ]]; then
    if [[ "$(id -u)" -ne 0 ]]; then
        echo "LaunchDaemon presente: richiede sudo per rimuoverlo." >&2
        echo "Esegui: sudo $0" >&2
        exit 1
    fi
    launchctl bootout "system/${LABEL}" 2>/dev/null || true
    rm -f "${DAEMON_PLIST}"
    echo "Rimosso LaunchDaemon: ${DAEMON_PLIST}"
    REMOVED=1
fi

if [[ "${REMOVED}" -eq 0 ]]; then
    echo "Nessun job ${LABEL} trovato."
else
    echo "Servizio notifiche agenda disinstallato."
fi
