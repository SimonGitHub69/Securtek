#!/bin/bash
# Installa il servizio di invio automatico email agenda su macOS (launchd).
# Controlla in loop continuo; intervallo e spegnimento da Securtek → Parametri mail.
#
# Uso:
#   ./deploy/macos/install-agenda-notifiche.sh
#   sudo ./deploy/macos/install-agenda-notifiche.sh --daemon
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUNNER="${ROOT}/deploy/macos/run-agenda-notifiche.sh"
LABEL="com.securtek.agenda-notifiche"
LOG_DIR="${ROOT}/logs"
MODE="agent"

usage() {
    cat <<'EOF'
Uso: install-agenda-notifiche.sh [--daemon]

  --daemon   Installa LaunchDaemon (richiede sudo; parte senza login)

L'orario di invio, l'intervallo di controllo e lo spegnimento si impostano in
Securtek → Agenda → Parametri mail.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --daemon)
            MODE="daemon"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Argomento sconosciuto: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if [[ ! -x "${ROOT}/.venv/bin/python" ]]; then
    echo "Python virtuale non trovato: ${ROOT}/.venv/bin/python" >&2
    exit 1
fi

chmod +x "${RUNNER}"
mkdir -p "${LOG_DIR}"

if [[ "${MODE}" == "daemon" ]]; then
    if [[ "$(id -u)" -ne 0 ]]; then
        echo "Il modo --daemon richiede sudo." >&2
        echo "Esegui: sudo $0 --daemon" >&2
        exit 1
    fi

    RUN_USER="${SUDO_USER:-}"
    if [[ -z "${RUN_USER}" || "${RUN_USER}" == "root" ]]; then
        echo "Impossibile determinare l'utente non-root (SUDO_USER)." >&2
        exit 1
    fi

    RUN_HOME="$(dscl . -read "/Users/${RUN_USER}" NFSHomeDirectory 2>/dev/null | awk '{print $2}')"
    if [[ -z "${RUN_HOME}" ]]; then
        RUN_HOME="$(eval echo "~${RUN_USER}")"
    fi
    RUN_GROUP="$(id -gn "${RUN_USER}")"
    RUN_UID="$(id -u "${RUN_USER}")"

    PLIST_SRC="${ROOT}/deploy/macos/com.securtek.agenda-notifiche.daemon.plist"
    PLIST_DST="/Library/LaunchDaemons/${LABEL}.plist"
    AGENT_PLIST="${RUN_HOME}/Library/LaunchAgents/${LABEL}.plist"

    chown "${RUN_USER}:${RUN_GROUP}" "${LOG_DIR}"

    if [[ -f "${AGENT_PLIST}" ]]; then
        launchctl bootout "gui/${RUN_UID}/${LABEL}" 2>/dev/null || true
        rm -f "${AGENT_PLIST}"
        echo "Rimosso LaunchAgent utente: ${AGENT_PLIST}"
    fi
    launchctl bootout "system/${LABEL}" 2>/dev/null || true

    TMP_PLIST="$(mktemp /tmp/com.securtek.agenda-notifiche.XXXXXX.plist)"
    sed \
        -e "s|__PROJECT_ROOT__|${ROOT}|g" \
        -e "s|__RUN_USER__|${RUN_USER}|g" \
        -e "s|__RUN_GROUP__|${RUN_GROUP}|g" \
        -e "s|__RUN_HOME__|${RUN_HOME}|g" \
        "${PLIST_SRC}" > "${TMP_PLIST}"

    install -o root -g wheel -m 644 "${TMP_PLIST}" "${PLIST_DST}"
    rm -f "${TMP_PLIST}"

    launchctl bootstrap system "${PLIST_DST}"
    launchctl enable "system/${LABEL}" 2>/dev/null || true

    echo
    echo "LaunchDaemon installato: ${PLIST_DST}"
    echo "Esegue come: ${RUN_USER}:${RUN_GROUP}"
    echo "Loop continuo; intervallo e spegnimento da Parametri mail."
    echo "Parte anche senza login (Mac Mini server)."
    echo "Log: ${LOG_DIR}/agenda-notifiche.log"
    echo
    echo "Prova immediata:"
    echo "  sudo -u ${RUN_USER} ${RUNNER} --dry-run"
    echo "  sudo -u ${RUN_USER} ${RUNNER} --force"
else
    PLIST_SRC="${ROOT}/deploy/macos/com.securtek.agenda-notifiche.plist"
    PLIST_DST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
    DOMAIN="gui/$(id -u)"

    mkdir -p "${HOME}/Library/LaunchAgents"

    sed -e "s|__PROJECT_ROOT__|${ROOT}|g" "${PLIST_SRC}" > "${PLIST_DST}"

    launchctl bootout "${DOMAIN}/${LABEL}" 2>/dev/null || true
    launchctl bootstrap "${DOMAIN}" "${PLIST_DST}"
    launchctl enable "${DOMAIN}/${LABEL}" 2>/dev/null || true

    echo
    echo "LaunchAgent installato: ${PLIST_DST}"
    echo "Loop continuo; intervallo e spegnimento da Parametri mail."
    echo "Log: ${LOG_DIR}/agenda-notifiche.log"
    echo
    echo "Sul Mac Mini server preferisci:"
    echo "  sudo ./deploy/macos/install-agenda-notifiche.sh --daemon"
    echo
    echo "Prova immediata:"
    echo "  ${RUNNER} --dry-run"
    echo "  ${RUNNER} --force"
fi
