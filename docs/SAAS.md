# Distribuzione cliente e percorso SaaS

## Implementato

Workspace operativo con utenti e ruoli, fonti configurabili, ricerche persistenti,
revisioni, scenari, inbox, audit e provider opzionali. Un'installazione per cliente:
database, volume snapshot, processo worker, segreti e eventuale profilo Hermes
separati. `WORKSPACE_ID` e `WORKSPACE_NAME` sono identificazione e display, **non
una barriera multi-tenant**. Gli utenti autorizzati vedono tutto il workspace.

L'architettura separa UI/API, calcoli, collector, storage e runtime AI. Per questo
non è necessario costruire un nuovo Hermes generalista né legare i dati a un
provider LLM. I contratti verticali sono nel nostro codice; il runtime rimane
sostituibile.

## Non ancora implementato

Self-signup, inviti via email con token, billing, abbonamenti, provisioning
self-service, SSO, MFA, quote per tenant, Postgres/RLS, coda distribuita, object
storage remoto, isolamento multi-tenant condiviso e procedure di cancellazione
per tenant. Non vendere questa release come se li comprendesse.

## Prima di un servizio pubblico condiviso

Scegliere prima il modello di isolamento e di autorizzazione. Ogni query/export,
job/task AI, nota/snapshot, notifica e chiave deve essere tenant-scoped con test
negativi cross-tenant. Introdurre migrazioni versionate verso Postgres, locking
worker distribuito, retry idempotenti e limiti per cliente. Separare configurazione
operatore da configurazione cliente. Aggiungere provisioning reversibile,
revoca account, quote, gestione abbonamenti e ripristino provato.

Definire retention, cancellazione, trattamento dati, diritti delle fonti e incident
response per la distribuzione effettiva. I controlli del codice non equivalgono a
un'autorizzazione commerciale dei portali né a una certificazione di conformità.

Questo elenco delimita lavoro futuro; non è codice nascosto già disponibile.
