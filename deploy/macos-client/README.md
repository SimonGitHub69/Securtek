# Securtek — installer client macOS

Per ogni **Mac client** (stessa rete del Mac Mini server). Non installa Django.

Sul Mini il selettore cartelle funziona perché helper e Finder sono lì.
Sul Mac client, senza questo installer, il clic su **Scegli cartella** non apre nulla
(il Finder comparirebbe sul server).

## Cosa installa

- Helper locale su `http://127.0.0.1:18765` (Scegli / Apri cartella sul **questo** Mac)
- Avvio automatico al login (LaunchAgent)
- **Securtek.app** sul Desktop (finestra Edge/Chrome verso il Mini)

## Requisiti sul Mac client

- Stessa rete del server
- **Microsoft Edge** (consigliato) o **Google Chrome**
- **Python 3** (`python3` nel Terminale). Se manca:

```bash
xcode-select --install
```

oppure installer da https://www.python.org/downloads/

Niente PostgreSQL, Gunicorn o copia del progetto Django.

## Installazione

1. Copia sul Mac client **tutta** la cartella `deploy/macos-client/`
   (USB, AirDrop, condivisione).
2. Se macOS blocca il file: tasto destro su `InstallClient.command` → **Apri**.
   Se non parte, nel Terminale:

```bash
cd ~/Downloads/macos-client
chmod +x InstallClient.command install-client.sh
xattr -dr com.apple.quarantine .
./InstallClient.command
```
3. Doppio clic su **InstallClient.command**.
4. Inserisci l’URL del Mini, ad esempio `http://192.168.2.76:8000`.
5. Alla prima selezione cartella, se compare “controllare Finder”, premi **Consenti**.

Verifica helper:

```bash
curl http://127.0.0.1:18765/health
```

Deve rispondere `{"ok": true, ...}`.

Poi apri **Securtek.app** dal Desktop (non Safari).

Da Terminale (opzionale):

```bash
SECURTEK_ORIGIN=http://192.168.2.76:8000 ./install-client.sh
```

## Dopo l’installazione sul server

Sul Mini, dopo aver aggiornato Securtek, serve anche lo script cartelle nuovo:

```bash
python manage.py collectstatic --noinput
sudo launchctl kickstart -k system/com.securtek.gunicorn
```

Senza questo passo il client potrebbe ancora chiamare il selettore del server.

## Disinstallazione

```bash
launchctl bootout "gui/$(id -u)/com.securtek.desktop-helper"
rm -f "${HOME}/Library/LaunchAgents/com.securtek.desktop-helper.plist"
rm -rf "${HOME}/Library/Application Support/Securtek/desktop-helper"
rm -rf "${HOME}/Desktop/Securtek.app"
```

## Nota sui file

Scegli/Apri usano i dischi **del Mac client**. L’anteprima elenco file in Securtek
legge ancora dal Mini: se la cartella non è visibile anche sul server (condivisione
di rete), l’elenco può risultare vuoto.
