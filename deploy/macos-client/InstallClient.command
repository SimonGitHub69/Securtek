#!/bin/bash
# Doppio clic su questo file sul Mac CLIENT (stessa rete del Mini).
# Installa helper cartelle + Securtek.app. Non serve Django sul client.

cd "$(dirname "$0")" || exit 1

# Fine riga Windows → Unix (se la cartella è copiata da un PC)
perl -pi -e 's/\r\n?/\n/g' ./install-client.sh ./InstallClient.command ./securtek_desktop_helper.py 2>/dev/null || true
chmod +x ./install-client.sh

./install-client.sh
status=$?

echo
if [[ "${status}" -eq 0 ]]; then
  echo "Installazione completata. Puoi chiudere questa finestra."
else
  echo "Installazione non completata (codice ${status})."
fi
echo
read -r -p "Premi Invio per chiudere..." _
exit "${status}"
