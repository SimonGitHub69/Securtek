#!/bin/bash
# Crea Securtek.app sul Desktop (niente Terminale al doppio clic).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="${HOME}/Desktop/Securtek.app"
BIN="${OUT}/Contents/MacOS"
RES="${OUT}/Contents/Resources"

# Cambia qui l'IP del server Securtek
ORIGIN="http://192.168.2.76:8000"

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
	<string>1.0</string>
	<key>CFBundleShortVersionString</key>
	<string>1.0</string>
	<key>LSMinimumSystemVersion</key>
	<string>11.0</string>
	<key>NSHighResolutionCapable</key>
	<true/>
</dict>
</plist>
EOF

cat > "${OUT}/Contents/MacOS/Securtek" <<EOF
#!/bin/bash
ORIGIN="${ORIGIN}"
LOGIN="\${ORIGIN}/login/?app=1"
PROFILE="\${HOME}/Library/Application Support/SecurtekApp"
mkdir -p "\${PROFILE}"

CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
EDGE_BIN="/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"

if [[ -x "\${CHROME_BIN}" ]]; then
  "\${CHROME_BIN}" --app="\${LOGIN}" --user-data-dir="\${PROFILE}" --no-first-run --no-default-browser-check --disable-features=InsecureDownloadWarnings >/dev/null 2>&1 &
elif [[ -x "\${EDGE_BIN}" ]]; then
  "\${EDGE_BIN}" --app="\${LOGIN}" --user-data-dir="\${PROFILE}" --no-first-run --no-default-browser-check --disable-features=InsecureDownloadWarnings >/dev/null 2>&1 &
else
  osascript -e 'display alert "Securtek" message "Chrome o Edge non trovati. Installali e riprova." as critical'
  exit 1
fi
exit 0
EOF

# Forza LF e permesso esecuzione
perl -pi -e 's/\r\n?/\n/g' "${OUT}/Contents/MacOS/Securtek"
chmod +x "${OUT}/Contents/MacOS/Securtek"

echo "Creata: ${OUT}"
echo "Doppio clic su Securtek.app — niente Terminale."
echo "Cambia ORIGIN nel file Contents/MacOS/Securtek se serve un altro IP."
