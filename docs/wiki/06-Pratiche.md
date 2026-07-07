# Pratiche

Il modulo Pratiche gestisce il ciclo operativo dei lavori svolti per un cliente.
Una pratica raccoglie dati amministrativi, soggetti coinvolti, stati di avanzamento,
scadenze, documenti e note operative.

## Obiettivo

Centralizzare tutto cio che serve per seguire una pratica dall'apertura alla
chiusura, mantenendo tracciabilita e collegamento con le Anagrafiche.

## Entita principali

- Pratica: contenitore principale del lavoro.
- Cliente: anagrafica collegata alla pratica.
- Referente: persona di contatto del cliente, quando disponibile.
- Stato pratica: fase corrente del ciclo di lavorazione.
- Scadenza: data da monitorare, interna o verso il cliente.
- Documento: file o riferimento documentale collegato.
- Attivita: nota operativa, evento o passaggio rilevante.

## Ciclo di vita

- Bozza: pratica creata ma non ancora avviata.
- Aperta: pratica attiva e presa in carico.
- In lavorazione: sono in corso verifiche, richieste o produzione documenti.
- In attesa cliente: bloccata da informazioni, documenti o conferme del cliente.
- In attesa esterna: bloccata da enti, fornitori o soggetti terzi.
- Completata: lavoro concluso positivamente.
- Annullata: pratica chiusa senza completamento.
- Archiviata: pratica storicizzata e non piu operativa.

## Informazioni minime

- Codice pratica progressivo o leggibile.
- Titolo o oggetto sintetico.
- Cliente collegato ad Anagrafica.
- Tipologia pratica.
- Stato corrente.
- Priorita.
- Data apertura.
- Data scadenza prevista.
- Responsabile interno.
- Descrizione e note.

## Regole operative

- Ogni pratica deve avere un cliente.
- Una pratica attiva non deve essere eliminata fisicamente: si usa soft delete.
- Le pratiche chiuse restano consultabili per storico e audit.
- Le scadenze superate devono essere evidenziate nelle liste e nella dashboard.
- I cambi stato devono essere tracciabili.
- I documenti collegati non devono essere persi quando la pratica viene archiviata.

## Prime viste previste

- Elenco pratiche con ricerca, filtri per stato, cliente, priorita e scadenza.
- Dettaglio pratica con dati principali, timeline, scadenze e documenti.
- Form creazione/modifica pratica.
- Azione rapida di cambio stato.
- Vista scadenze pratiche.

## Permessi iniziali

- Utente autenticato: lettura delle pratiche assegnate o visibili al proprio gruppo.
- Operatore: creazione e aggiornamento delle pratiche.
- Responsabile: assegnazione, cambio stato avanzato e archiviazione.
- Admin: gestione completa e configurazioni.

## Integrazioni

- Anagrafiche: collegamento cliente e futuri referenti.
- Dashboard: conteggi per stato, pratiche in scadenza e pratiche bloccate.
- Documenti: allegati e modelli collegati alla pratica.
- Agenda: promemoria e scadenze operative.
