# SECURTEK

## Changelog

Tutte le modifiche importanti del progetto saranno documentate in questo file.

Il formato segue le linee guida di Keep a Changelog.

---

# [0.2.0-alpha] - 2026-07-07

## 🎉 Architettura

- Creata la struttura definitiva del progetto.
- Configurato Django 6.
- Configurato PostgreSQL.
- Inizializzato repository Git.

## Core

- Creato BaseModel.
- Creato BaseAdmin.
- Creato BaseForm.
- Definita la struttura delle applicazioni.

```
apps/
├── accounts/
├── agenda/
├── anagrafiche/
├── core/
├── dashboard/
└── pratiche/
```

## Frontend

Installati:

- Tabler
- Bootstrap 5
- HTMX
- Alpine.js

## Layout

Realizzati:

- layout.html
- sidebar.html
- navbar.html
- footer.html
- messages.html

## Dashboard

- Creata Dashboard iniziale.
- Creato componente KPI (`stats_card.html`).
- Predisposto caricamento dati tramite `get_context_data()`.

## Static

Organizzazione definitiva:

```
static/
└── securtek/
    ├── css/
    ├── js/
    ├── img/
    ├── fonts/
    └── icons/
```

## UI

- Sidebar personalizzata.
- Navbar personalizzata.
- Inizio Design System SECURTEK.

## Refactoring

- Riorganizzati i template.
- Preparata la struttura per componenti riutilizzabili.

---

# [0.3.0-alpha] (In sviluppo)

## Previsto

- Dashboard professionale
- Tabelle
- Form
- Modali
- Tema SECURTEK
- Menu dinamico

---

# [0.4.0-alpha] (Pianificato)

## Core

- Login
- Permessi
- Gruppi
- Audit Log
- Configurazioni

---

# [0.5.0-alpha] (Pianificato)

## Modulo Anagrafiche

- Clienti
- Aziende
- Contatti

---

# [0.6.0-alpha] (Pianificato)

## Modulo Pratiche

- Workflow
- Allegati
- Note
- Stato pratica

---

# [1.0.0]

Prima release stabile.