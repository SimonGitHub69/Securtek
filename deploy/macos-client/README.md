# Securtek — installer client macOS (v0.2.1 — aggiorna file VERSION in questa cartella)

Per ogni **Mac client** (stessa rete del Mac Mini server). Non installa Django.

## Versione

- File **`VERSION`** in questa cartella (deve coincidere con il server).
- Sul server: footer / login **Securtek v. …** oppure `curl http://IP-MINI:8000/version/`
- Dopo `install-client.sh` il Terminale mostra `Securtek: v…`

Per ogni rilascio: aggiorna `VERSION` nella root del progetto e in `deploy/macos-client/VERSION`.

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
   Se compare *«non hai i privilegi di accesso adeguati»*, apri **Terminale** e incolla:

```bash
cd ~/Downloads/macos-client
chmod +x InstallClient.command install-client.sh create-app.sh CreateApp.command
xattr -dr com.apple.quarantine .
bash install-client.sh
```

(`bash install-client.sh` funziona anche senza permesso di esecuzione sul file.)

   Se la cartella non è in Download, cambia il percorso, ad esempio:

```bash
cd ~/Desktop/macos-client
bash install-client.sh
```
3. Doppio clic su **InstallClient.command**.
4. Inserisci l’URL del Mini, ad esempio `http://192.168.2.76:8000`.
5. Alla fine il Finder **mostra Securtek.app** sul Desktop (cartella `Desktop` o `Scrivania`).
6. Alla prima selezione cartella, se compare “controllare Finder”, premi **Consenti**.

### Solo Securtek.app (senza helper)

Se ti serve solo l’icona per aprire Securtek:

```bash
./CreateApp.command
```

oppure `SECURTEK_APP_ONLY=1 ./install-client.sh`

### Non vedi Securtek.app?

L’app **non** è nel repository Git: va **generata** sul Mac con uno script sopra.
Controlla nel Terminale:

```bash
ls -la ~/Desktop/Securtek.app
open -R ~/Desktop/Securtek.app
```

Se il percorso non esiste, l’installer non è arrivato in fondo (Python mancante, URL annullato, cartella incompleta).

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

## Scegli cartella non funziona (Mac client)

Il browser blocca spesso le chiamate dirette a `127.0.0.1` dalla pagina del Mini.
Serve **helper v2** + **JS aggiornato** sul server:

**Sul Mini:**

```bash
python manage.py collectstatic --noinput
sudo launchctl kickstart -k system/com.securtek.gunicorn
```

**Sul Mac client** (ricopia `macos-client` aggiornato):

```bash
cd ~/Downloads/macos-client
bash install-client.sh
bash repair-app.sh
```

Poi chiudi e riapri Securtek.app. Alla selezione cartella si apre una **mini finestra locale** e poi il **Finder**.

Se compare «Popup bloccato», consenti i popup per Edge/Chrome.

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
