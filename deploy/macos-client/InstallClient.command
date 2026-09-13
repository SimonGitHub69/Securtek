#!/bin/bash
# Doppio clic su questo file sul Mac CLIENT (stessa rete del Mini).
# Installa helper cartelle + Securtek.app. Non serve Django sul client.
# Funziona anche senza bit di esecuzione sugli altri file (usa bash).

cd "$(dirname "$0")" || exit 1
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:/usr/local/bin:${PATH:-}"

xattr -dr com.apple.quarantine . 2>/dev/null || true
perl -pi -e 's/\r\n?/\n/g' \
  ./install-client.sh \
  ./InstallClient.command \
  ./securtek_desktop_helper.py \
  ./SecurtekLauncher.template \
  ./InstallaSecurtek \
  ./create-app.sh \
  ./CreateApp.command \
  ./repair-app.sh 2>/dev/null || true
chmod +x ./install-client.sh ./InstallClient.command ./create-app.sh ./CreateApp.command ./repair-app.sh ./InstallaSecurtek 2>/dev/null || true

/bin/bash ./install-client.sh
status=$?

echo
if [[ "${status}" -eq 0 ]]; then
  echo "Installazione completata. Puoi chiudere questa finestra."
else
  echo "Installazione non completata (codice ${status})."
fi
echo
if [[ -t 0 ]]; then
  read -r -p "Premi Invio per chiudere..." _
fi
exit "${status}"
