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

read_securtek_version() {
  local candidate line
  for candidate in "${ROOT}/../macos-client/VERSION" "${ROOT}/../../VERSION"; do
    if [[ -f "${candidate}" ]]; then
      line="$(head -n1 "${candidate}" | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
      if [[ -n "${line}" ]]; then
        printf '%s' "${line}"
        return 0
      fi
    fi
  done
  printf '%s' "0.0.0"
}

SECURTEK_VERSION="$(read_securtek_version)"

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
	<string>${SECURTEK_VERSION}</string>
	<key>CFBundleShortVersionString</key>
	<string>${SECURTEK_VERSION}</string>
	<key>LSMinimumSystemVersion</key>
	<string>11.0</string>
	<key>NSHighResolutionCapable</key>
	<true/>
</dict>
</plist>
EOF

TEMPLATE="${ROOT}/../macos-client/SecurtekLauncher.template"
if [[ ! -f "${TEMPLATE}" ]]; then
  echo "Template mancante: ${TEMPLATE}" >&2
  exit 1
fi
cp "${TEMPLATE}" "${OUT}/Contents/MacOS/Securtek"
perl -pi -e "s|__ORIGIN__|${ORIGIN}|g; s|__BROWSER__|${BROWSER}|g" "${OUT}/Contents/MacOS/Securtek"
perl -pi -e 's/\r\n?/\n/g' "${OUT}/Contents/MacOS/Securtek"
chmod +x "${OUT}/Contents/MacOS/Securtek"
xattr -cr "${OUT}" 2>/dev/null || true
if command -v codesign >/dev/null 2>&1; then
  codesign -s - --force --deep "${OUT}" 2>/dev/null || true
fi

echo "Creata: ${OUT}"
echo "Versione: ${SECURTEK_VERSION}"
echo "Browser preferito: ${BROWSER} (fallback: l'altro tra Edge/Chrome)"
echo "Elimina eventuali vecchie Securtek.app prima di usare questa."
echo "Doppio clic su Securtek.app — finestra dedicata, senza Safari/Chrome normale."
echo "Per forzare Chrome: BROWSER=chrome ./deploy/macos/build-securtek-app.sh"
echo "Cambia ORIGIN in Contents/MacOS/Securtek se serve un altro IP."
