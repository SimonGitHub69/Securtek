#!/bin/bash
# Crea Securtek.app sul Desktop — finestra dedicata (Edge/Chrome --app), niente Safari.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="${HOME}/Desktop/Securtek.app"
BIN="${OUT}/Contents/MacOS"
RES="${OUT}/Contents/Resources"

# Cambia qui l'IP del server Securtek
ORIGIN="http://192.168.2.76:8000"
# edge | chrome (Safari non supporta modalità app)
BROWSER="${BROWSER:-edge}"

mkdir -p "${BIN}" "${RES}"

cat > "${OUT}/Contents/Info.plist" <<EOF
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

cat > "${OUT}/Contents/MacOS/Securtek" <<'LAUNCHER'
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

# Sostituisci placeholder (evita problemi con ${} nel heredoc)
perl -pi -e "s|__ORIGIN__|${ORIGIN}|g; s|__BROWSER__|${BROWSER}|g" "${OUT}/Contents/MacOS/Securtek"
perl -pi -e 's/\r\n?/\n/g' "${OUT}/Contents/MacOS/Securtek"
chmod +x "${OUT}/Contents/MacOS/Securtek"

echo "Creata: ${OUT}"
echo "Browser preferito: ${BROWSER} (fallback: l'altro tra Edge/Chrome)"
echo "Elimina eventuali vecchie Securtek.app prima di usare questa."
echo "Doppio clic su Securtek.app — finestra dedicata, senza Safari/Chrome normale."
echo "Per forzare Chrome: BROWSER=chrome ./deploy/macos/build-securtek-app.sh"
echo "Cambia ORIGIN in Contents/MacOS/Securtek se serve un altro IP."
