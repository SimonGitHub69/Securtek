#!/bin/bash
# Installer postazione Mac CLIENT (niente Django/PostgreSQL).
# Installa: helper cartelle (LaunchAgent al login) + Securtek.app sul Desktop.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_ORIGIN="${SECURTEK_ORIGIN:-http://192.168.2.76:8000}"
BROWSER="${BROWSER:-edge}"
LABEL="com.securtek.desktop-helper"
DOMAIN="gui/$(id -u)"
APP_SUPPORT="${HOME}/Library/Application Support/Securtek"
HELPER_DIR="${APP_SUPPORT}/desktop-helper"
LOG_DIR="${HOME}/Library/Logs/Securtek"
PLIST_DST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
APP_OUT="${HOME}/Desktop/Securtek.app"

strip_cr() {
  local f
  for f in "$@"; do
    if [[ -f "${f}" ]] && grep -q $'\r' "${f}" 2>/dev/null; then
      perl -pi -e 's/\r\n?/\n/g' "${f}"
    fi
  done
}

alert() {
  local message="$1"
  osascript -e "display alert \"Securtek\" message \"${message}\" as critical" 2>/dev/null || echo "${message}" >&2
}

info() {
  local message="$1"
  osascript <<EOF >/dev/null 2>&1 || echo "${message}"
display dialog "${message}" buttons {"OK"} default button "OK" with title "Securtek"
EOF
}

find_python() {
  local candidate
  for candidate in \
    "$(command -v python3 2>/dev/null || true)" \
    /usr/bin/python3 \
    /opt/homebrew/bin/python3 \
    /usr/local/bin/python3
  do
    if [[ -n "${candidate}" && -x "${candidate}" ]]; then
      printf '%s' "${candidate}"
      return 0
    fi
  done
  return 1
}

find_helper_src() {
  if [[ -f "${HERE}/../../scripts/securtek_desktop_helper.py" ]]; then
    printf '%s' "${HERE}/../../scripts/securtek_desktop_helper.py"
    return 0
  fi
  if [[ -f "${HERE}/securtek_desktop_helper.py" ]]; then
    printf '%s' "${HERE}/securtek_desktop_helper.py"
    return 0
  fi
  return 1
}

ask_origin() {
  if [[ -n "${SECURTEK_ORIGIN:-}" ]]; then
    printf '%s' "${SECURTEK_ORIGIN}"
    return 0
  fi
  local result
  result="$(osascript <<EOF
try
  set dlg to display dialog "URL del server Securtek (Mac Mini):" default answer "${DEFAULT_ORIGIN}" with title "Installazione client Securtek" buttons {"Annulla", "Installa"} default button "Installa" cancel button "Annulla"
  return text returned of dlg
on error
  return ""
end try
EOF
)" || true
  printf '%s' "${result}"
}

strip_cr "${HERE}/install-client.sh" "${HERE}/InstallClient.command" "${HERE}/securtek_desktop_helper.py" || true

ORIGIN="$(ask_origin)"
ORIGIN="${ORIGIN%"${ORIGIN##*[![:space:]]}"}"
ORIGIN="${ORIGIN#"${ORIGIN%%[![:space:]]*}"}"
ORIGIN="${ORIGIN%/}"

if [[ -z "${ORIGIN}" ]]; then
  echo "Installazione annullata."
  exit 1
fi

if [[ ! "${ORIGIN}" =~ ^https?:// ]]; then
  alert "URL non valido. Usa ad esempio http://192.168.2.76:8000"
  exit 1
fi

HELPER_SRC="$(find_helper_src || true)"
if [[ -z "${HELPER_SRC}" ]]; then
  alert "Helper non trovato. Tieni securtek_desktop_helper.py nella stessa cartella di questo installer."
  exit 1
fi

PYTHON3="$(find_python || true)"
if [[ -z "${PYTHON3}" ]]; then
  alert "Python 3 non trovato. Installa Command Line Tools (Terminale: xcode-select --install) oppure Python da python.org, poi rilancia InstallClient."
  exit 1
fi

strip_cr "${HELPER_SRC}" || true

mkdir -p "${HELPER_DIR}" "${LOG_DIR}" "${HOME}/Library/LaunchAgents"
cp "${HELPER_SRC}" "${HELPER_DIR}/securtek_desktop_helper.py"
chmod 755 "${HELPER_DIR}/securtek_desktop_helper.py"

cat > "${PLIST_DST}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON3}</string>
        <string>${HELPER_DIR}/securtek_desktop_helper.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${HELPER_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ProcessType</key>
    <string>Interactive</string>
    <key>LimitLoadToSessionType</key>
    <string>Aqua</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>LANG</key>
        <string>it_IT.UTF-8</string>
        <key>LC_ALL</key>
        <string>it_IT.UTF-8</string>
    </dict>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/desktop-helper.out.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/desktop-helper.err.log</string>
</dict>
</plist>
EOF

launchctl bootout "${DOMAIN}/${LABEL}" 2>/dev/null || true
launchctl bootout "${DOMAIN}" "${PLIST_DST}" 2>/dev/null || true
sleep 1

if ! launchctl bootstrap "${DOMAIN}" "${PLIST_DST}" 2>/tmp/securtek-client-launchctl.err; then
  echo "bootstrap fallito, provo load -w..." >&2
  cat /tmp/securtek-client-launchctl.err >&2 || true
  launchctl load -w "${PLIST_DST}"
fi

launchctl enable "${DOMAIN}/${LABEL}" 2>/dev/null || true
launchctl kickstart -k "${DOMAIN}/${LABEL}" 2>/dev/null || true

BIN="${APP_OUT}/Contents/MacOS"
RES="${APP_OUT}/Contents/Resources"
mkdir -p "${BIN}" "${RES}"

cat > "${APP_OUT}/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleExecutable</key>
	<string>Securtek</string>
	<key>CFBundleIdentifier</key>
	<string>local.securtek.app</string>
	<key>CFBundleName</key>
	<string>Securtek</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleVersion</key>
	<string>1.3</string>
	<key>CFBundleShortVersionString</key>
	<string>1.3</string>
	<key>LSMinimumSystemVersion</key>
	<string>11.0</string>
	<key>NSHighResolutionCapable</key>
	<true/>
</dict>
</plist>
EOF

cat > "${APP_OUT}/Contents/MacOS/Securtek" <<'LAUNCHER'
#!/bin/bash
ORIGIN="__ORIGIN__"
BROWSER="__BROWSER__"
LOGIN="${ORIGIN}/login/?app=1"
PROFILE="${HOME}/Library/Application Support/SecurtekApp"
mkdir -p "${PROFILE}"

APP_FLAGS=(
  --app="${LOGIN}"
  --user-data-dir="${PROFILE}"
  --unsafely-treat-insecure-origin-as-secure="${ORIGIN}"
  --test-type
  --no-first-run
  --no-default-browser-check
  --no-startup-window
  --disable-session-crashed-bubble
  --disable-features=TranslateUI,InsecureDownloadWarnings,BlockInsecurePrivateNetworkRequests
)

launch_edge() {
  local EDGE_BIN="/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
  [[ -x "${EDGE_BIN}" ]] || return 1
  exec "${EDGE_BIN}" "${APP_FLAGS[@]}" >/dev/null 2>&1 &
}

launch_chrome() {
  local CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  [[ -x "${CHROME_BIN}" ]] || return 1
  exec "${CHROME_BIN}" "${APP_FLAGS[@]}" >/dev/null 2>&1 &
}

show_missing_browser() {
  osascript -e 'display alert "Securtek" message "Installa Microsoft Edge o Google Chrome per aprire Securtek come applicazione." as critical' 2>/dev/null || true
}

case "${BROWSER}" in
  chrome)
    launch_chrome || launch_edge || show_missing_browser
    ;;
  edge|*)
    launch_edge || launch_chrome || show_missing_browser
    ;;
esac
exit 0
LAUNCHER

perl -pi -e "s|__ORIGIN__|${ORIGIN}|g; s|__BROWSER__|${BROWSER}|g" "${APP_OUT}/Contents/MacOS/Securtek"
perl -pi -e 's/\r\n?/\n/g' "${APP_OUT}/Contents/MacOS/Securtek"
chmod +x "${APP_OUT}/Contents/MacOS/Securtek"

sleep 1
HEALTH_OK=0
if curl -fsS "http://127.0.0.1:18765/health" >/tmp/securtek-helper-health.json; then
  HEALTH_OK=1
fi

echo "Server: ${ORIGIN}"
echo "Python: ${PYTHON3}"
echo "Helper: ${HELPER_DIR}/securtek_desktop_helper.py"
echo "App:    ${APP_OUT}"

if [[ "${HEALTH_OK}" -eq 1 ]]; then
  echo "OK — helper in ascolto su http://127.0.0.1:18765/"
  info "Client Securtek installato. Helper cartelle attivo. Apri Securtek.app sul Desktop (${ORIGIN}). Alla prima selezione cartella, se macOS chiede di controllare Finder, premi Consenti."
else
  echo "ATTENZIONE: health non risponde. Log: ${LOG_DIR}/desktop-helper.err.log" >&2
  alert "App creata, ma l'helper cartelle non risponde. Controlla ${LOG_DIR}/desktop-helper.err.log oppure rilancia InstallClient dopo aver installato Python 3."
  exit 1
fi
