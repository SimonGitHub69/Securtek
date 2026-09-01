# Securtek App — accesso consigliato

Gli utenti devono aprire Securtek **dall’app** (finestra Chrome/Edge `--app`),
non dal browser con schede. Stesso modello di LabRepair.

## Architettura tipica

| Ruolo | Macchina | Cosa fa |
|-------|----------|---------|
| Server | Mac Tahoe | Django + PostgreSQL |
| Client | PC Windows (o Mac) | Solo l’app Securtek sul Desktop |

## Client Windows

1. Copia sul PC utente la cartella `deploy/windows/` (almeno `SecurtekApp.vbs` + `SecurtekApp.bat`).
2. In `SecurtekApp.vbs` imposta l’URL del Mac server, ad esempio:

```vb
Origin = "http://192.168.1.50:8000"
```

3. Doppio clic su `SecurtekApp.bat` → crea anche il collegamento **Securtek** sul Desktop.
4. Gli utenti usano sempre quel collegamento.

Comportamento:
- apre `http://SERVER/login/?app=1` in finestra app (senza barra indirizzi)
- chiudi con la **X** → logout automatico
- riapri → schermata di login

## Client Mac (altra postazione, stessa rete)

Copia `deploy/macos-client/` sul Mac utente e fai doppio clic su **InstallClient.command**.
Installa helper cartelle + `Securtek.app`. Dettagli: `deploy/macos-client/README.md`.

## Nota

Aprendo Securtek dal browser normale l’app funziona comunque, ma **senza**
logout automatico alla chiusura. Per lo studio, distribuisci solo il collegamento app.
