# Architettura e invarianti

## Una base piccola, con confini sostituibili

Un processo FastAPI serve API e UI statica. SQLite WAL conserva dati e coda. Un solo worker elabora le run; nessun Redis, Celery, microservizio fittizio o build frontend è necessario per la preview. Hermes resta esterno, integrato tramite il suo contratto HTTP documentato.

Il backend non importa moduli privati di Hermes e non richiede un fork. Le ricerche salvate nella UI sono configurazioni di prodotto, non processi Hermes separati per ciascun cliente. Ogni turno remoto usa un nuovo `session_id=vedra-<run-id>`.

## Acquisizione

`Engine.enqueue` salva uno snapshot dei criteri. L’indice SQLite `one_active_run_per_agent` impedisce due run attive per la stessa ricerca. Un secondo click restituisce la run esistente.

Ogni fonte restituisce un `Listing` Pydantic. Il connettore recupera le pagine, rispetta limiti e blocchi, scopre link locali, estrae dati JSON-LD/CSS. L’importazione passa attraverso lo stesso schema di normalizzazione. L’origine demo/reale viene assegnata dalla fonte o dall’importazione esplicita, non dal modello.

`upsert_listing` usa `source_id + listing_key` e l’hash dei contenuti. Nessuna duplicazione dello stesso annuncio a ogni heartbeat. Gli aggiornamenti non cancellano preferiti, note o stato della revisione umana. Il vecchio prezzo rimane in `observations` e lo snapshot grezzo viene conservato come `.txt`, non servito come HTML eseguibile.

L’entity resolution tra portali è soltanto una lista di candidati: stesso indirizzo normalizzato, comune e tipologia, superficie entro 3%. Unità diverse nello stesso palazzo restano possibili; nessun merge automatico.

## Classificazione e responsabilità

- In modalità `local`, espressioni regolari leggono segnali espliciti. La UI indica “Regole locali”, mai AI simulata.
- In modalità `hermes`, la raccolta deterministica avviene prima del turno AI. Gli immobili nuovi/cambiati, o già raccolti ma non ancora analizzati da Hermes, diventano task se superano i filtri numerici fondamentali.
- Se non esistono task semantici, non parte alcuna chiamata al modello.
- Se esistono task, Vedra avvia Hermes. Le skills invocano il bridge autenticato; `collect` restituisce i dati già acquisiti, senza rifare lo scraping.
- Il bridge espone al massimo 10 task pendenti per risposta. Dopo ogni blocco la skill chiede lo stato successivo. Titolo e un estratto di descrizione (massimo 6.000 caratteri) costituiscono l’evidenza; un eventuale troncamento è dichiarato.
- Ogni task è legato all’hash della fonte. Una revisione successiva provoca 409, non l’applicazione di un’analisi obsoleta.
- Ogni strategia richiede una citazione presente nel titolo/estratto. Il server rifiuta chiavi extra, strategie duplicate e citazioni inesistenti. Questa validazione non equivale a verificare semanticamente o tecnicamente l’affermazione.
- `finish` viene accettato solo quando ogni task è stato presentato. Il worker osserva anche la conclusione effettiva della run Hermes: una frase “ho finito” non basta.

Nessun output LLM può scrivere prezzo, superficie, benchmark, score o SQL tramite il bridge. Il riassunto e le strategie sono comunque inferenze da sottoporre a verifica umana. Le skills non sono una sandbox: vedere SECURITY.

## Scheduler e stato

L’orologio del prodotto è nel backend: frequenza 0 = manuale; minimo automatico 15 minuti. Le scadenze sono conservate in UTC, rese nel fuso del browser. Il prossimo avvio è programmato dalla conclusione del precedente, non è un cron wall-clock e non accumula backlog di ogni intervallo perso.

“Attivo” consente gli avvii pianificati. “Pausa” ferma gli avvii futuri, non una run in corso. “Annulla” interrompe cooperativamente il lavoro e richiede lo stop remoto a Hermes; dati già acquisiti restano tracciati. In caso di riavvio le run attive vengono segnate `interrupted`, non dichiarate completate; quelle ancora accodate restano eseguibili.

Un cron esterno Hermes può usare `bridge enqueue` soltanto quando l’agente ha frequenza Manuale e non è in pausa. Evita due scheduler sullo stesso workflow. Non avviare l’app con più worker Uvicorn: questa preview ha un solo proprietario della coda.

## Stati osservabili

`queued`, `running`, `cancelling`, `completed`, `partial`, `failed`, `cancelled`, `interrupted`.

Una fonte con alcuni record errati può produrre una run `partial`. Zero link estratti non viene interpretato come “nessun immobile sul mercato”: il test fallisce indicando un possibile problema di mapping. Se nessuna fonte riesce, la run fallisce. Un errore Hermes non attiva un fallback nascosto in modalità locale.

La UI usa eventi SSE per i log e polling limitato per riallineare il workspace. La vista dei risultati comprende sia immobili nei criteri sia quelli acquisiti ma scartati: il pulsante **Nei criteri** e il filtro per ricerca isolano i qualificati.

## Evoluzioni, non capacità già presenti

Per molte fonti/utenti: migrare dati a PostgreSQL, code con lease distribuito, auth per tenant, oggetti con retention, rate limiting per cliente e policy di autorizzazione dei dataset. Connettori specifici vanno aggiunti dietro lo stesso schema, con fixture e test reali. Non servono modifiche al core di Hermes per queste estensioni.
