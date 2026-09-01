# Securtek — helper cartelle sul PC (Windows / macOS)

Quando Django gira sul **Mac Mini server** e apri Securtek dal **PC Windows**
(con cartelle tipo `D:/ALLEGATI_...`), il selettore/apertura sul server **non può**
vedere i dischi del PC.

Serve questo **helper locale** sul computer dove usi il browser.

## Cosa fa

- Ascolta solo su `http://127.0.0.1:18765`
- **Scegli cartella** → finestra nativa sul PC
- **Apri cartella** → Explorer (Windows) o Finder (Mac)

## Windows (ogni postazione)

1. Copia sul PC la cartella progetto (o almeno `scripts/securtek_desktop_helper.py`
   + `deploy/windows/SecurtekDesktopHelper.bat` + `.vbs`).
2. Doppio clic su `deploy/windows/SecurtekDesktopHelper.bat`
3. (Consigliato) Metti un collegamento a quel `.bat` in:
   `shell:startup` (Esegui → shell:startup)
4. Verifica: apri nel browser `http://127.0.0.1:18765/health`
   → deve rispondere `{"ok": true, ...}`

Poi in Securtek → Modifica pratica → Categorie:
- icona **+ cartella** = Scegli
- icona **cartella aperta** = Apri in Explorer

## macOS client (altro Mac in rete, non il Mini)

Copia `deploy/macos-client/` sul Mac e fai doppio clic su **InstallClient.command**.
Vedi `deploy/macos-client/README.md`.

Avvio manuale (debug):

```bash
python3 scripts/securtek_desktop_helper.py
```

## Nota

- L’occhio (anteprima elenco file) legge ancora i file **dal server Django**.
  Se i file sono solo sul PC Windows, l’anteprima può risultare vuota finché
  i path non esistono anche sul server (condivisione di rete).
- Scegli/Apri funzionano sul PC grazie all’helper.
