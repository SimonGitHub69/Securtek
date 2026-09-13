# Securtek — installer client macOS

Per ogni **Mac client** (stessa rete del Mac Mini server). Non installa Django.

## Installer autoinstallante (consigliato)

Da Windows (cartella progetto):

```bat
scripts\build-macos-client-installer.bat
```

oppure PowerShell:

```powershell
.\scripts\build-macos-client-installer.ps1
```

Output in `dist/`:

- **`Securtek-client-mac-vVERSION.zip`** — da copiare sul Mac client
- **`InstallaSecurtek-vVERSION.command`** — file unico (AirDrop)
- cartella `securtek-client-mac-vVERSION/` con **Installa Securtek.app**

Sul Mac client:

1. Estrai lo zip.
2. Doppio clic su **Installa Securtek**.
   Se macOS blocca: tasto destro → **Apri** → **Apri**.
3. Inserisci l’URL del Mini, ad esempio `http://192.168.2.76:8000`.
4. Sul Desktop compare **Securtek.app**.

File unico: doppio clic su `InstallaSecurtek.command`. Se compare *«non hai i privilegi»*:

```bash
bash ~/Downloads/InstallaSecurtek.command
```

(`bash` non richiede il permesso di esecuzione sul file.)

## Versione

- File **`VERSION`** in questa cartella (deve coincidere con il server).
- Lo script di build copia `VERSION` dalla root del progetto e l’helper da `scripts/securtek_desktop_helper.py`.
- Sul server: footer / login **Securtek v. …** oppure `curl http://IP-MINI:8000/version/`

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
- **Python 3** (`python3` nel Terminale). Se manca, l’installer propone `xcode-select --install`

Niente PostgreSQL, Gunicorn o copia del progetto Django.

## Installazione dalla cartella `macos-client` (alternativa)

1. Copia sul Mac client **tutta** la cartella `deploy/macos-client/`
   (USB, AirDrop, condivisione).
2. Doppio clic su `InstallClient.command`.
   Se macOS blocca: tasto destro → **Apri**.
   Se compare *«non hai i privilegi di accesso adeguati»*:

```bash
cd ~/Downloads/macos-client
bash InstallClient.command
```

3. Inserisci l’URL del Mini, ad esempio `http://192.168.2.76:8000`.
4. Alla fine il Finder **mostra Securtek.app** sul Desktop (cartella `Desktop` o `Scrivania`).
5. Alla prima selezione cartella, se compare “controllare Finder”, premi **Consenti**.

### Solo Securtek.app (senza helper)

```bash
./CreateApp.command
```

oppure `SECURTEK_APP_ONLY=1 bash install-client.sh`

### Non vedi Securtek.app?

L’app **non** è nel repository Git: va **generata** sul Mac con l’installer.
Controlla nel Terminale:

```bash
ls -la ~/Desktop/Securtek.app
open -R ~/Desktop/Securtek.app
```

Log installer: `~/Library/Logs/Securtek/install-client.log`

Verifica helper:

```bash
curl http://127.0.0.1:18765/health
```

Deve rispondere `{"ok": true, ...}`.

Poi apri **Securtek.app** dal Desktop (non Safari).

Da Terminale (opzionale):

```bash
SECURTEK_ORIGIN=http://192.168.2.76:8000 bash install-client.sh
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
Serve **helper aggiornato** + **JS aggiornato** sul server:

**Sul Mini:**

```bash
python manage.py collectstatic --noinput
sudo launchctl kickstart -k system/com.securtek.gunicorn
```

**Sul Mac client:** riesegui **Installa Securtek** (o `bash install-client.sh` nella cartella).

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
