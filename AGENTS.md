# Regole di sviluppo Vedra

Lavora su cambiamenti circoscritti e testabili. Riutilizza le primitive frontend di
`ui.js`, il client `api.js`, i driver database e i servizi esistenti. Commenta motivi,
vincoli e compromessi non ovvi; non descrivere ogni riga.

Nessun seed o mock nel percorso operativo. Le fixture sono esclusivamente in
`backend/tests/`. Non inserire segreti, annunci di terzi o font binari nel repository.

Acquisizione, permessi e calcoli sono codice; AI solo interpretazione con evidenze.
Non sostituire errori o campioni insufficienti con dati plausibili. Non implementare
bypass, proxy evasivi o accesso a endpoint privati dei portali.

Mantieni equivalenza SQLite/PostgreSQL: qmark parameters, SQL nel sottoinsieme
controllato del progetto, migrazioni additive, transazioni esplicite per compare-and-write.
Non usare rowid o PRAGMA nei servizi di dominio. Un solo worker per workspace.

Esegui pytest, controlli JS/mappa, test processi e UI. I test PostgreSQL richiedono un
DB usa-e-getta con TEST_DATABASE_URL; mai un progetto cliente. Documenta gli skip.
Non dichiarare un deployment o una chiamata modello riusciti senza una prova.

Per le skill di sviluppo UI segui `docs/DESIGN.md`; per le skill dell’agente immobiliare
segui `hermes/skills/`. Sono due sistemi distinti. Non ampliare i tool di Hermes per
aggirare una validazione fallita.
