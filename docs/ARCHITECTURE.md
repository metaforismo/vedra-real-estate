# Architettura 0.3

```text
Vercel: HTML, CSS e moduli JS → rewrite HTTPS /api/*
                                       ↓
VPS: API FastAPI (senza worker implicito) → schema privato PostgreSQL/Supabase
                                       ↑                 ↑
VPS: un worker Vedra → collector → storico → filtri → analisi → risultati
                                       ↓
                  regole | provider diretto | Hermes ristretto
```

In locale `start.sh` usa SQLite e avvia il worker nel processo API. Nel deployment
cloud, API e worker sono processi separati. Il browser non interroga direttamente
Supabase, non riceve chiavi del DB e non accede al gateway Hermes. Gli snapshot e
la cache immagini rimangono nel volume privato della VPS condiviso da API/worker.

## Confini

`db_drivers.py` isola connessioni e transazioni; `db.py` mantiene il contratto del
repository. Il supporto PostgreSQL usa SQL parametrizzato, pool di connessioni e
schema privato. Il piccolo traduttore dei placeholder riguarda solo il sottoinsieme
SQL controllato dell'app, non una API per query SQL arbitrarie.

`engine.py` conserva configurazioni e run; i servizi separati trattano acquisizione,
classificazione, calcoli, notifiche, immagini e insight. Il clock è di Vedra, non
dell'LLM. Un indice univoco impedisce due run attive dello stesso agente. Un lock
file (SQLite) o un advisory lock di sessione (PostgreSQL) ammette un solo worker.
La perdita della connessione che detiene il lock ferma il worker; non prosegue
senza esclusività. Il secondo processo legge lo stato dal database, non dalla
memoria dell'API.

## Migrazioni e consistenza

Le migrazioni sono additive. La v3 conserva il contesto del prezzo a ogni nuova
osservazione: valuta, tipo di transazione, base e quantità della superficie.
Non ricostruisce il passato a partire da un annuncio modificato oggi. Sessioni e
capabilities non passano nella migrazione SQLite→PostgreSQL; gli utenti accedono
nuovamente. Il target deve essere vuoto. Vedi `UPGRADE.md`.

L'app continua a utilizzare JSON serializzato per contratti/documenti e testi ISO
UTC per timestamp, con la stessa semantica nei due database. Non dichiarare questo
lavoro come una conversione completa a ORM, PostGIS, multi-tenancy o coda distribuita.

## Modello AI

Il risultato semantico deve citare estratti della revisione ricevuta. L'LLM non
scrive importi, score, SQL o file. La presenza di una citazione non certifica che
l'interpretazione sia corretta: strategia e fattibilità richiedono revisione umana.
Le skills sono istruzioni, mentre il server applica autorizzazioni e validazioni.
