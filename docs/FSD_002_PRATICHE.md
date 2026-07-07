# FSD-002 - Pratiche

## Stato

Bozza funzionale.

## Contesto

Il progetto ha gia una base per Dashboard, layout e Anagrafiche. Il modulo
Pratiche e il passo successivo naturale: deve collegare il lavoro operativo ai
clienti censiti in Anagrafica e fornire una traccia chiara dello stato di ogni
attivita.

## Scope iniziale

La prima versione del modulo deve permettere di:

- creare una pratica collegata a un'Anagrafica;
- consultare e cercare le pratiche attive;
- filtrare per stato, priorita, cliente e scadenza;
- aggiornare i dati principali;
- vedere il dettaglio con stato, note e date principali;
- chiudere o archiviare una pratica senza cancellazione fisica.

Fuori scope per la prima versione:

- workflow configurabile da interfaccia;
- gestione documentale avanzata;
- automazioni email;
- integrazioni con enti esterni;
- calendario completo.

## Modello dati proposto

### Pratica

Campi principali:

- uuid, audit e soft delete tramite `BaseModel`;
- codice;
- titolo;
- descrizione;
- cliente, foreign key verso `Anagrafica`;
- stato;
- priorita;
- tipologia;
- data_apertura;
- data_scadenza;
- data_chiusura;
- responsabile;
- note.

### Stato pratica

Per la prima versione puo essere una scelta statica nel modello:

- bozza;
- aperta;
- in_lavorazione;
- in_attesa_cliente;
- in_attesa_esterna;
- completata;
- annullata;
- archiviata.

In una versione successiva potra diventare una tabella configurabile.

### Priorita

Valori iniziali:

- bassa;
- normale;
- alta;
- urgente.

## Regole di business

- Il cliente e obbligatorio.
- Il codice pratica deve essere univoco.
- Una pratica completata o annullata deve valorizzare `data_chiusura`.
- Una pratica archiviata non compare di default nelle liste operative.
- Una pratica con `data_scadenza` passata e stato non finale e scaduta.
- Il cambio stato deve aggiornare `updated_at` e, quando possibile, `updated_by`.

## UX minima

### Lista pratiche

La lista deve mostrare:

- codice;
- titolo;
- cliente;
- stato;
- priorita;
- responsabile;
- scadenza;
- azioni principali.

Filtri iniziali:

- ricerca testuale su codice, titolo e cliente;
- stato;
- priorita;
- scadenze scadute o imminenti.

### Dettaglio pratica

Il dettaglio deve mostrare:

- intestazione con codice, titolo, stato e priorita;
- dati cliente;
- date principali;
- descrizione e note;
- azioni modifica, cambio stato e archiviazione.

### Form pratica

Il form deve includere:

- titolo;
- cliente;
- tipologia;
- stato;
- priorita;
- data scadenza;
- responsabile;
- descrizione;
- note.

## Dipendenze tecniche

- `apps.anagrafiche.models.Anagrafica`;
- `apps.core.models.BaseModel`;
- autenticazione Django gia presente nelle viste Anagrafiche;
- componenti template esistenti per pagine, form e tabelle.

## Debiti tecnici da chiudere prima del codice

- Rimuovere le definizioni duplicate di `AnagraficaCreateView` e
  `AnagraficaUpdateView`.
- Decidere se i file modello vuoti in `apps/anagrafiche/models/` sono placeholder
  intenzionali o vanno eliminati.
- Escludere o ripulire i file `__pycache__` modificati dalla working tree.
- Stabilizzare le migrazioni Anagrafiche prima di creare foreign key da Pratiche.

## Criteri di accettazione

- `manage.py check` senza errori.
- Migrazioni generate e applicabili.
- Lista pratiche accessibile solo ad utenti autenticati.
- Creazione pratica con cliente obbligatorio.
- Ricerca e filtri funzionanti.
- Pratiche archiviate escluse dalla lista operativa.
- Dettaglio pratica raggiungibile dalla lista.
