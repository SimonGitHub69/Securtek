#!/bin/bash
# Securtek App (macOS) — finestra dedicata Edge/Chrome --app (niente Safari, niente open -na).
#
# 1) Modifica ORIGIN con l'URL del server Mac
# 2) Opzionale: BROWSER=edge|chrome
# 3) sed -i '' $'s/\r$//' SecurtekApp.command && chmod +x SecurtekApp.command
# 4) Doppio clic per avviare

set -euo pipefail

ORIGIN="http://192.168.2.76:8000"
BROWSER="${BROWSER:-edge}"

LOGIN="${ORIGIN}/login/?app=1"
PROFILE="${HOME}/Library/Application Support/SecurtekApp"
mkdir -p "${PROFILE}"

APP_FLAGS=(
  --app="${LOGIN}"
  --user-data-dir="${PROFILE}"
  --unsafely-treat-insecure-origin-as-secure="${ORIGIN},http://127.0.0.1:18765"
  --test-type
  --no-first-run
  --no-default-browser-check
  --no-startup-window
  --disable-session-crashed-bubble
  --disable-features=TranslateUI,InsecureDownloadWarnings,BlockInsecurePrivateNetworkRequests,PrivateNetworkAccessSendPreflights,PrivateNetworkAccessRespectPreflightResults
)

launch_edge() {
  local EDGE_BIN="/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
  [[ -x "${EDGE_BIN}" ]] || return 1
  "${EDGE_BIN}" "${APP_FLAGS[@]}" >/dev/null 2>&1 &
}

launch_chrome() {
  local CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  [[ -x "${CHROME_BIN}" ]] || return 1
  "${CHROME_BIN}" "${APP_FLAGS[@]}" >/dev/null 2>&1 &
}

case "${BROWSER}" in
  chrome)
    launch_chrome || launch_edge
    ;;
  edge|*)
    launch_edge || launch_chrome
    ;;
esac

osascript >/dev/null 2>&1 <<'APPLESCRIPT' &
tell application "Terminal"
  try
    close front window
  end try
end tell
APPLESCRIPT

exit 0
