# Prompt per completare Vedra su Oracle

Incolla il testo seguente nel task Codex con accesso alla VM Oracle. Gli accessi,
i domini e il progetto Supabase devono essere risolti prima delle operazioni dipendenti.
Non incollare password nel prompt. Questo è un piano operativo, non una prova di deploy.

---

Configura e collauda Vedra dal repository https://github.com/metaforismo/vedra-real-estate.
La prima ricerca è Milano, appartamenti in vendita da 500.000 a 600.000 EUR,
inizialmente manuale e limitata a 3 annunci. Usa examples/milano-500-600k.criteria.json.
Il modello Regolo qwen3.8-27b ha già superato catalogo e classificazione diretta;
Hermes remoto resta da verificare. La creazione Supabase gratuita ha fallito per
quota: non ripeterla senza risolvere lo slot o scegliere PostgreSQL su Oracle.

Voglio un workspace reale: frontend Vercel, API e worker sulla mia VM Oracle,
PostgreSQL Supabase e un profilo Hermes dedicato con Regolo. Non riscrivere Hermes.
Usa anche le modifiche preparate nel branch locale codex/live-setup, se disponibili;
non presumere che quel branch sia già pubblicato su GitHub.

## Contesto e accessi

1. Leggi AGENTS.md, docs/CLOUD.md, docs/HERMES.md e docs/AI.md. Controlla branch,
   commit, modifiche locali, processi, porte, RAM e spazio della VM prima di installare.
   Il precedente task Oracle è codex://threads/01a02658-41d2-7c73-abc2-df5dfbf54ee1.
   Nella precedente sessione Hermes era in /home/ubuntu/.hermes/hermes-agent/venv/bin/hermes
   e /home/ubuntu/.local/bin/hermes: verifica nuovamente i percorsi e la versione.
2. Conserva l'Hermes personale Maia, i suoi servizi, cron, memoria e credenziali.
   Crea Vedra sotto un utente di servizio dedicato, con home e profilo propri.
   Non usare né copiare la home personale come home del servizio.
3. Prima di creare Supabase chiedi l'organizzazione e verifica/conferma i costi con
   il connettore. L'ultima ricognizione vedeva metaforismo's Org, ID
   muhjewkpodeaticyxdhm; non riusare i database di altri prodotti.
   Per Vercel risultava team_G4qxd2ESJKmAgvPIZRQyTeI3, metaforismos-projects.
   Ricontrolla entrambi prima di agire.
4. Risolvi dominio frontend, dominio API e accesso SSH/Cloud Shell. Chiedi solo ciò
   che manca, senza inventare URL o considerare disponibili vecchie sessioni.

## Configurazione

5. Installa una copia versionata in /opt/vedra e un virtualenv Python 3.11+.
   Installa requirements-cloud.txt e requirements-hermes.txt. Evita Docker se
   l'installazione nativa già disponibile basta. Usa un solo processo API e un worker.
6. Esegui scripts/setup.py una sola volta con output privato; genera .env con permessi
   0600. Non mostrare chiavi, password o DATABASE_URL in chat, log, commit o screenshot.
   Configura PUBLIC_ORIGIN con l'origine frontend definitiva, COOKIE_SECURE=true,
   ALLOWED_HOSTS con i soli host necessari, WORKER_ENABLED=false per l'API,
   SCHEDULER_ENABLED=true, DATA_DIR=/opt/vedra/data e WORKSPACE_NAME=Vedra.
7. In un progetto Supabase dedicato applica deploy/supabase.sql. Imposta in privato
   la password del ruolo vedra_app e DATABASE_URL con TLS, DATABASE_SCHEMA=vedra,
   DATABASE_POOL_SIZE=4. Usa connessione diretta/session pooler sulla porta 5432,
   mai transaction pooler 6543. Non esporre lo schema vedra nella Data API.
   Il browser usa l'autenticazione Vedra; non riceve credenziali database/service_role.
8. Installa e adatta deploy/vedra-api.service.example e vedra-worker.service.example.
   Il codice e il virtualenv sono leggibili dal servizio; solo data/ deve essere
   scrivibile. Verifica /api/health e heartbeat persistente del worker.
9. Configura HTTPS usando deploy/Caddyfile.example e DNS del dominio API. API su
   127.0.0.1:8000; gateway Hermes su 127.0.0.1:8645; /bridge e /bridge/* bloccati
   dal reverse proxy. Verifica porte/firewall Oracle prima di modificare regole.
10. Crea/importa il progetto Vercel dalla radice della repo. vercel.json usa
    python3 scripts/build_vercel.py. Imposta solo VEDRA_API_ORIGIN=https://DOMINIO_API
    come variabile build. Non aggiungere chiavi AI o PostgreSQL su Vercel.
    Verifica /api/health attraverso il dominio frontend, cookie Secure, login e CSRF.
    Le preview casuali non vanno aggiunte con wildcard a PUBLIC_ORIGIN.

## Regolo e Hermes

11. L'allegato propone https://api.regolo.ai/v1 e il model ID qwen3.8-27b, ma la sua
    descrizione cita Qwen3.6-27b: verifica il catalogo autenticato e una richiesta
    reale prima di dichiararlo supportato. Chiedi l'autorizzazione esplicita all'uso
    della chiave dell'allegato verso Regolo e al piccolo test a consumo, se manca.
    Non sostituire automaticamente il modello con un altro.
12. Configura il provider nel profilo Vedra, con credenziale privata. Per la prova
    diretta il repository include examples/regolo.local.env.example:
    AI_API_BASE_URL=https://api.regolo.ai/v1, AI_MODEL=qwen3.8-27b,
    AI_REASONING_EFFORT=xhigh, AI_RESPONSE_FORMAT=json_object,
    AI_MAX_OUTPUT_TOKENS=4000, AI_TIMEOUT_SECONDS=120, AI_MAX_ANALYSES_PER_RUN=5.
    Le tariffe dell'allegato non sono una tariffa verificata. Verifica compatibilità
    dei parametri e consumi effettivi; non mascherare errori con un fallback.
13. Con l'utente di servizio crea il profilo Hermes vedra e configura il provider.
    Esegui con il Python del virtualenv Vedra:
    python scripts/configure_hermes.py --profile vedra
    Avvia hermes -p vedra gateway come servizio persistente separato. Usa il profilo
    dell'utente corretto, non quello di ubuntu. Verifica che il processo MCP possa
    eseguire il Python e leggere hermes/mcp/server.py da /opt/vedra.
14. Verifica /v1/capabilities e /v1/toolsets autenticati: soltanto
    mcp_vedra_get_tasks, mcp_vedra_submit_analysis, mcp_vedra_finish_run.
    Se la versione Hermes non supporta il protocollo o espone altri tool, fermati e
    correggi l'integrazione; non ampliare i permessi. Nessun terminale o browser
    generalista nel profilo operativo. Vedra resta l'unico scheduler.

## Dati reali e collaudo

15. Chiedi città, criteri e fonte iniziale (feed/CSV cliente o sito utilizzabile).
    La raccolta è compito del collector Vedra: il modello classifica il testo,
    non è un connettore ai portali. Non dichiarare disponibili Idealista,
    Immobiliare.it o Casa.it senza un connettore concretamente verificato.
16. Inserisci solo i domini necessari in LIVE_ALLOWED_DOMAINS e separatamente in
    IMAGE_ALLOWED_DOMAINS. Configura la fonte e prova una ricerca/un annuncio.
    Conserva URL, timestamp, campi mancanti ed errori. Niente dati inventati o bypass
    di blocchi. Importa benchmark solo con fonte, periodo e segmento confrontabili.
17. Crea una ricerca manuale con massimo 3 annunci e poche analisi AI. Eseguila due
    volte: controlla deduplica, storico, citazioni, log, uso token e completamento.
    Prova anche arresto e riavvio worker. Attiva la periodicità solo dopo la verifica.
18. Esegui pytest, controlli JS/mappa/catalogo, test processi e UI. PostgreSQL usa
    esclusivamente un DB usa-e-getta tramite TEST_DATABASE_URL, mai il progetto live.
    Verifica desktop/mobile, stato vuoto, errore fonte, caricamento e dati incompleti.
19. Rimuovi dal prodotto i residui “demo/dimostrativa”, preservando stati vuoti,
    provenienza e limiti delle stime. Non eliminare i filtri backend che impediscono
    ai vecchi record sintetici di apparire come dati reali.
20. Consegna URL frontend/API, commit distribuito, servizi attivi, fonte utilizzata,
    risultato delle due run, limiti residui, istruzioni backup/ripristino e rollback.
    Distingui PASS, FAIL e NOT RUN. Non chiamare “live” un frontend privo di backend,
    un gateway raggiungibile senza analisi, o un catalogo senza acquisizione provata.
