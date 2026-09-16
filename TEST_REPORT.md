# Rapporto di verifica · Vedra 0.2.0

**16 settembre 2026.** Base: `ce6e3d96161d1800d06d842853f07aaffb52d780`.
Questa è la verifica dei sorgenti aggiornati inclusi nello ZIP, non quella della
precedente preview. Repository remoto non modificato.

## Risultati eseguiti

| Controllo | Esito |
|---|---|
| Backend `pytest -q` | **176 passed in 45.03s** |
| Sintassi Python `compileall` | Passata su backend, scripts e Hermes |
| Sintassi JavaScript | **10 moduli** validi |
| Test mappa Node | **8 asserzioni** passate |
| Browser Chromium + backend HTTP locale | **13 gruppi di flussi passati**, nessun errore JavaScript |
| Configurazione AI senza richiesta live | Chiave assente segnalata; nessuna richiesta inviata |

Comandi:

```bash
python -m pytest -q
python -m compileall -q backend hermes scripts
node scripts/check_frontend.mjs
node scripts/test_map.mjs
python scripts/test_ui.py --relay --chromium /usr/bin/chromium
```

I comandi UI qui usano il binario Chromium presente nell'ambiente. Nell'installazione
utente/CI, installare Playwright Chromium ed eseguire `python scripts/test_ui.py`
senza `--relay` per la navigazione HTTP diretta.

## Cosa coprono le prove nuove

Migrazione v1→v2 con riferimenti conservati e riapplicazione idempotente; runtime
`llm` registrabile; due run senza duplicare né richiamare il modello sugli invariati;
modifica del testo con nuova analisi; budget AI con residuo ripreso nella run
successiva; controlli temporali dei dettagli; variazioni prezzo e osservazioni;
lock del worker; cooldown e ripristino fonte; notifiche idempotenti, demo escluse
dalla coda SMTP; sitemap limitata, XML malformato/DTD/indici respinti.

Revisioni con owner, scadenza e checklist; 409 sulle modifiche concorrenti, anche
quando la fase è cambiata dalla vecchia API di review; ruoli viewer/editor;
scenari con aritmetica, validazione, salvataggio/lettura/eliminazione e valuta;
comparabili compatibili e rimozione dei duplicati confermati dal campione;
assenza di benchmark quando i metadati mancano; viste personali; inbox; cambio
password e revoca delle altre sessioni; audit e diagnostica.

Contratto AI con `httpx.MockTransport`: schema, citazioni, payload senza prezzi
né URL, token noti/sconosciuti, errori sanitizzati, 401/403/404/redirect, retry
limitato, rifiuto di output troncati o tool call, nessuna rete senza configurazione.
Hermes: capacità, lista esatta dei tre tool, stdio MCP, parametri invalidi,
capability limitata a run/scadenza, revoca e rifiuto dell'operazione collect.

## Verifica UI

1. Real workspace is empty by default
2. Login, real session and overview
3. Property detail and persisted team note
4. Pipeline stage, due date and human checklist persist
5. Scenario calculation, saved assumptions, reload and honest comparables
6. Benchmark inventory and inbox empty states
7. Personal saved view round trip
8. Selection, comparison, municipal filter and card view
9. Create, execute, inspect logs, pause and resume a real queued job
10. CSV file import through the actual browser form
11. Map point comes from imported coordinates and opens the matching stored property
12. Data quality and honest missing Hermes status
13. Dark theme and 393px mobile navigation without document overflow

Screenshot effettivi in `docs/screenshots/`: popolati da dati sintetici espliciti
oppure vuoti. La prova della mappa importa un record di test con coordinate e
verifica che il punto apra proprio quell'immobile nel database. Non è un annuncio
raccolto da un portale.

### Limite preciso del trasporto browser

Questo ambiente blocca la navigazione top-level di Chromium verso localhost con
`ERR_BLOCKED_BY_ADMINISTRATOR`. Il runner `--relay` rende il frontend e inoltra
le richieste al **backend HTTP reale**, senza fixture al posto delle API.
Il relay gestisce i cookie lato client HTTP e omette CSP dalla risposta di QA;
quindi **non certifica** cookie/CSP/CORS, navigazione diretta, HTTPS o reverse proxy
nel deployment finale. Gli header e l'autenticazione sono anche coperti dai test
backend. I flussi vanno ripetuti in modalità diretta nell'ambiente destinatario.

## Non verificato qui

Nessuna chiamata live a Regolo/Qwen o a un altro modello; nessuna sessione sul
Hermes dell'utente; nessuno scraping live dei portali target; nessun SMTP esterno,
Docker build/Compose o deployment pubblico HTTPS. Nessun test di carico o di
funzionamento per giorni. Nessuna misurazione della qualità semantica del modello
su un campione immobiliare reale, nessuna garanzia di copertura o disponibilità.

Le fixture non attestano accessibilità di fonti commerciali. Il `.env` iniziale è
vuoto per AI e allowlist, demo disabilitata. Per il collaudo reale:
[LOCAL_TEST](docs/LOCAL_TEST.md), [AI](docs/AI.md), [DATA](docs/DATA.md).

Ambiente verificato: Python 3.13.5, Node 22, Chromium di sistema. Le versioni
rilevate delle librerie e il dettaglio UI sono in [verification.json](docs/verification.json).
Il requisito minimo Python 3.11 non è una dichiarazione di test eseguito su ogni
versione supportata. Dipendenze transitive non bloccate da un lockfile completo.

## Archivio

Il packager esclude segreti, database, log privati, cache, ambienti virtuali,
file font, `.git` e materiali riservati. Lo ZIP contiene il repository completo e
`MANIFEST.sha256` per i sorgenti e gli asset inclusi. Il test di estrazione e
avvio del pacchetto viene riportato nel file `PACKAGE_CHECK.txt` accompagnatorio.
