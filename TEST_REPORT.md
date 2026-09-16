# Rapporto di verifica · Vedra 0.3.0

**16 settembre 2026.** Base remota verificata:
`6d4325bdfe0431df8b6dc261908cf114d8b8536f`, tree
`8536398e1294d496902b156c8437227a956ead01`. La copia iniziale era identica a questa
Git tree, prima delle modifiche. Non sono stati effettuati push, PR o merge remoti.

## Prove eseguite

| Controllo | Risultato locale |
|---|---|
| Suite backend e strumenti `pytest -q` | **249 passati, 3 saltati** (21,66 s nell'esecuzione completa) |
| Sintassi Python | `compileall` su backend, Hermes e scripts passato |
| Sintassi JavaScript | **12 moduli** validi |
| Invarianti mappa | **8** passate: vuoto, coordinate, raggruppamento, escape, limiti |
| API e worker in processi separati | **7 controlli** passati su HTTP reale e SQLite temporaneo |
| Browser Chromium e backend HTTP locale | **14 gruppi di flussi** passati; nessun errore JavaScript |
| Build Vercel | Configurazione e allowlist dei file testate; nessun deployment remoto |
| Migrazione dati | Trasferimento locale, rifiuto target non vuoto e rollback testati |
| Script PR/merge | Verifica remota, review/head/check mancanti o saltati coperti da test; nessuna pubblicazione live |

I **3 test saltati** sono integrazioni PostgreSQL: in questo ambiente mancano server
PostgreSQL e driver opzionali. La job `postgres` nella CI prepara PostgreSQL 16 ed
esegue questi test realmente. Il helper di pubblicazione non ammette merge finché
questa job, insieme a `tests`, non è verde. Non confondere la predisposizione della
CI con un'esecuzione remota già avvenuta.

## Cosa coprono le novità

Avvio senza catalogo demo anche in presenza del vecchio `.env.example`; rifiuto
importazioni/dataset legacy; pulizia transazionale esplicita che mantiene dati reali;
migrazioni idempotenti e nessun contesto storico inventato. Prezzi e variazioni
richiedono valuta, transazione e superficie omogenee. Segmenti con almeno cinque
asset distinti, duplicati confermati esclusi dal conteggio, aste/metadati ignoti
esclusi dai comparabili incompatibili, percentili assenti sotto la soglia.

Probe con città esplicita, campi mancanti, risultato persistito senza import;
429/backoff non aggirato dal pulsante di verifica. Foto solo host autorizzati,
magic raster, cache limitata, pause dopo blocchi e budget per immagine (non una
quota che blocca per sempre il processo dopo 200 richieste). Nessuna foto stock.

Shared heartbeat, worker fermo o con timestamp futuro, esclusione secondo worker,
riavvio con coda persistente e assenza di duplicazione. Contratti del driver
PostgreSQL e traduzione dei parametri testati localmente, ma non una connessione
Supabase. Build statica non include backend, dati, fixture o segreti.

Rimangono coperti i percorsi della 0.2: sessioni/CSRF/ruoli, acquisizione sicura,
normalizzazione, import/export, revisioni concorrenti, scenari deterministici,
inbox/outbox, contratti AI/Hermes, capability limitate alla run e citazioni.
I test del modello usano trasporti di test: non misurano la qualità di Qwen o di
un altro provider su immobili reali.

## Test di processi reali

`scripts/test_worker_processes.py` avvia API e worker separati con un database
locale temporaneo. Verifica: API vuota senza worker implicito; import e accodamento;
consumo della coda; rifiuto secondo worker; seconda run senza duplicare dati; stop
worker visibile mentre API rimane disponibile; riavvio riconnesso. I dati sono
fixture sintetiche importate esplicitamente dal collaudo, mai seed di prodotto.

## Test UI

Sono stati verificati: workspace vuoto; login; nota persistente; pipeline/owner/
scadenza/checklist; scenario salvato e comparabili; benchmark/inbox/insight; vista
personale; selezione/confronto/filtri/card; agente con run reale, log, pausa/ripresa;
import CSV dal form; punto mappa collegato all'immobile importato; qualità dati e
Hermes assente; tema scuro/mobile 393 px senza overflow; ricerca globale.

La navigazione diretta Chromium verso localhost è bloccata dall'ambiente con
`ERR_BLOCKED_BY_ADMINISTRATOR`. Il parametro `--relay` inoltra richieste al
**backend HTTP reale**, non a API simulate. Il relay gestisce cookie nel client
HTTP e omette la CSP in QA: **non certifica cookie nel browser, CSP, HTTPS o rewrite
Vercel**. La CI e il collaudo destinatario devono eseguire senza `--relay`.
Inter è configurato via Google Fonts ma il caricamento remoto è bloccato nel QA:
lo screenshot mostra il fallback locale. Nessun file font è distribuito.

Lo screenshot `docs/screenshots/dashboard.png` documenta l'app vuota. Le prove
popolate usano soltanto fixture isolate sotto `backend/tests/`, non annunci presi
dai portali. Le fixture non sono servite dal frontend né incluse nell'immagine
Docker applicativa.

## Comandi riproducibili

```bash
python -m pytest -q
python -m compileall -q backend hermes scripts
node scripts/check_frontend.mjs
node scripts/test_map.mjs
python scripts/test_worker_processes.py
python scripts/test_ui.py --relay --chromium /usr/bin/chromium
```

Su una macchina non soggetta al blocco di navigazione:

```bash
python -m playwright install chromium
python scripts/test_ui.py
```

La CI usa il browser Playwright installato e la navigazione diretta. Le fixture
sintetiche sono una risorsa di collaudo, non una modalità nell'app.

## Non verificato in questa consegna

Scraping live dei portali, provider LLM (Regolo o altri), Hermes reale, SMTP,
Docker/Compose, Supabase remoto, HTTPS pubblico e Vercel deployment. Nessuna prova
per giorni, benchmark di carico, validazione urbanistica o statistica di un modello
finanziario. Il prodotto è un'istanza dedicata per cliente: billing, self-signup e
isolamento multi-tenant condiviso non sono implementati.

## Pacchetto

ZIP con sorgenti completi e manifest SHA256; esclusi database, `.env`, credenziali,
font binari, cache e ambienti virtuali. Il rapporto di estrazione è in
`PACKAGE_CHECK.txt`. La patch include anche le cancellazioni, che una semplice
copia di file da ZIP sopra il vecchio clone non eseguirebbe. Vedi `docs/PR.md`.
