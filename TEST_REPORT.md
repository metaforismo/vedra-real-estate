# Verifiche Vedra 0.4.0

Data: 18 settembre 2026. Base GitHub verificata:
`f1a47fc1c5873992ab6cbb99e56770dfc141d2dc` (0.3.0).

## Risultati effettivi

| Verifica | Risultato locale |
|---|---|
| Suite Python | **296 passati, 4 saltati** |
| Nuovi test archivio/collaborazione/storia | **46 passati** |
| JavaScript | **14 moduli** con sintassi valida |
| Frontend funzionale | **7 test**: concorrenza, cancellazione, errori, debounce, selezioni e login senza sessione |
| Mappa | **8 invarianti** passate |
| API + worker separati | **7 controlli** passati, processi reali |
| UI + backend HTTP locale | **18 gruppi di flussi**, nessun errore JavaScript |
| Python compileall | Passato |
| Build Vercel | Output generato con origin HTTPS di test; non è un deployment |

I quattro skip sono integrazioni PostgreSQL: qui mancano il server e i driver
opzionali. La CI `postgres` contiene ora anche la prova di ricerca, storia e batch
review. Deve passare realmente prima del merge insieme alla job `tests`; né gli
skip né l’assenza dei check sono considerati successo dal helper PR.

## Prove della 0.4

Un archivio di **2.006 annunci sintetici di test** verifica la lettura dei record oltre
il precedente limite, la navigazione in 21 pagine senza duplicati su un database
fermo, i conteggi, le opzioni geografiche e gli export filtrati. L’esportazione troppo
ampia viene rifiutata: non produce un file apparentemente completo ma troncato.

Filtri parametrizzati, caratteri %, _, ! e apostrofi letterali; no interferenza di
sintassi SQL, valute obbligatorie nei range economici, valori non finiti rifiutati,
superfici mancanti, filtri combinati e qualificazione riferita allo specifico agente.
Record sintetici legacy esclusi; proiezione delle strategie coerente con le analisi.

Revisione multipla: rollback completo in caso di record/versione in conflitto, nessuna
nota o audit parziale, no-op, nota obbligatoria per scarto, conservazione di responsabile,
scadenza e checklist, permessi viewer e CSRF. Trasferimento di indici e osservazioni
verso un DB vuoto, rollback del target non vuoto, migrazione ripetibile.

Cronologia: confronto dei valori effettivamente registrati, nessuna modifica ai dati
passati dopo una nuova analisi, pagina con predecessore corretto, cursore limitato
all’immobile, valuta precedente e successiva e mancata retro-compilazione delle
vecchie osservazioni. Un’acquisizione invariata non crea una storia fittizia.

Preflight: runtime senza chiavi, fonte assente/disabilitata, allowlist, permesso,
browser, cooldown futuro/malformato, worker assente e import statico. Nessuna richiesta
HTTP o modello per la diagnostica. Una nuova configurazione invalida il vecchio test
fonte senza cancellare il backoff operativo.

## Interfaccia e trasporto del test

Collegamento reale al backend locale: login, import, note, scenari, comparabili,
revisione, pipeline, selezione tra pagine, batch edit, filtri avanzati, errore 422
correggibile, cronologia, agenti con job eseguito, pausa/ripresa, mappa, viste salvate,
fonte, diagnostica, tema scuro, mobile 393 px e reduced motion. Selezione anche nelle
schede e conservazione del focus. Il controller ha ulteriori test Node per risposte
fuori ordine e annullamento: un vecchio errore non copre risultati più recenti.
Il rendering della schermata di accesso viene verificato anche senza stato autenticato
o DOM, a copertura di una regressione individuata e corretta nel collaudo del pacchetto.

La navigazione diretta di Chromium è bloccata con `ERR_BLOCKED_BY_ADMINISTRATOR`.
Il parametro `--relay` inoltra le richieste al **backend HTTP reale**, non a risposte
API simulate. I cookie sono gestiti dal client HTTP e la CSP è omessa nel relay:
**non è una validazione di cookie del browser, CSP, HTTPS o proxy Vercel**. In CI e
nell’ambiente destinatario usare il test senza `--relay`.

Inter è configurato, ma il caricamento remoto è disabilitato nel collaudo: le immagini
usano il fallback di sistema. Nessun file font è incluso. Gli screenshot di release
mostrano stati vuoti; le prove popolate usano fixture sintetiche sotto `backend/tests`,
mai seed o annunci fittizi nel runtime. Nessun modello ha generato quei risultati QA.

## Processi e riproduzione

Il test processi avvia API e worker separatamente su database temporaneo: archivio vuoto,
import, coda, worker consumatore, secondo worker respinto, seconda run senza duplicati,
arresto osservabile e riconnessione. Non è una prova di continuità per giorni.

```bash
python -m pytest -q
python -m compileall -q backend hermes scripts
node scripts/check_frontend.mjs
node scripts/test_map.mjs
node scripts/test_catalog.mjs
python scripts/test_worker_processes.py
python -m playwright install chromium
python scripts/test_ui.py
```

Nell’ambiente ristretto usato per questo lavoro:
`python scripts/test_ui.py --chromium /usr/bin/chromium --relay`.

## Limiti e pubblicazione

Non testati: PostgreSQL reale, Supabase remoto, Vercel/HTTPS, Docker, SMTP, scraping
di portali reali, Hermes/provider AI reali e funzionamento per giorni. Il prodotto
rimane un’istanza dedicata per cliente, senza billing, self-signup o multitenancy
condivisa dichiarati. I test di classificazione verificano contratti ed evidenze,
non la qualità di un modello su un portafoglio immobiliare reale.

Il connettore GitHub di questa sessione offre letture, non scritture. Git dal container
non risolve github.com e GitHub CLI non è disponibile. Nessuna PR, push o merge è stato
eseguito. `scripts/publish_pr.py` è predisposto con base 0.3 corretta e branch 0.4,
senza override amministrativi. La verifica del pacchetto è in `PACKAGE_CHECK.txt`.

## Copia estratta

La suite è stata rieseguita dalla copia estratta: **296 passati, 4 saltati**.
Dopo la correzione della regressione nel login sono stati rieseguiti con successo
tutti i **18 gruppi UI** e i **7 controlli API/worker**. Il manifest e la patch
permettono di confrontare esattamente i sorgenti distribuiti.

## 2026-09-23 — browser navigation and UI states

- Full suite with `BROWSER_TEST_EXECUTABLE` set to the installed Chrome: 362 passed,
  4 PostgreSQL tests skipped (no disposable PostgreSQL URL configured).
- Native Chromium integration rechecked after redirect interception: JavaScript
  discovers the link, the detail is persisted, a same-source redirect succeeds,
  and redirects outside the source or into a robots-excluded path are rejected
  before those fixture endpoints receive a request.
- 19 real-HTTP local UI scenarios passed, including source browser-setting
  persistence, desktop/mobile, reduced motion and dark mode; no page errors.
- 7 separate-process checks, 15 JS module syntax checks, 8 map invariants and
  7 catalog tests passed.
- The browser integration check uses an isolated local fixture server. It is not
  evidence of portal coverage, a model call, or a production deployment.
- Production API and existing Hermes toolset remain reachable. The new seven-tool
  profile and frontend have not been deployed in this pass; live activation waits
  for administrative access. No secrets or real listing contents enter the package.

## 2026-09-23 — verifica dopo l'attivazione live

- 362 test Python passati, quattro integrazioni PostgreSQL saltate in assenza di
  un database temporaneo configurato. La prova Chromium include ora 30 script
  statici e mantiene i controlli sui redirect prima del contatto con la destinazione.
- 15 moduli JavaScript, 8 invarianti mappa, 7 test catalogo e 7 controlli dei processi
  passati nuovamente.
- Verifica interattiva su backend HTTP locale isolato: login, attesa Hermes con
  conteggi ancora assenti, interruzione, mobile a 393 px e tema scuro. Nessun
  overflow orizzontale o errore JavaScript osservato. I dati sono fixture QA,
  non annunci reali e non sono stati trasferiti al workspace operativo.
- L'ultimo collaudo UI completo (19 scenari) precede questa correzione circoscritta.
- Runtime live a sette tool verificato; ricerca fallita per timeout del provider.
  Il login visivo live non è stato completato in questa verifica.

- Dopo il deploy della correzione il test fonte con browser nativo è passato
  (catalogo, 10 link nella prima pagina e un dettaglio). Nove endpoint live
  rispondono HTTP 200; scheduler ogni 360 minuti attivo; hash degli asset UI
  pubblicati uguali ai sorgenti verificati. Non è un ciclo Hermes completato.

## 2026-09-23 — ricerca browser e seconda fonte

- Ciclo Hermes live completato: 20 link scoperti, quattro acquisizioni/verifiche,
  tre aggiornamenti, zero errori. Gli annunci venduti sono stati riconosciuti
  autonomamente. Nessun risultato compatibile con il budget in quella fonte.
- 372 test Python passati con Chromium; quattro test PostgreSQL saltati senza
  database temporaneo. Dieci regressioni coprono località esplicite, stato,
  negazioni e precedenza dei dati strutturati.
- 15 moduli JS, otto controlli mappa, sette test catalogo e sette controlli dei
  processi passati. Collaudo UI mirato su HTTP locale: menu mobile escluso
  dall'accessibilità quando chiuso, navigazione, schede agenti a 393 px senza
  contenuti tagliati, tema scuro. Fixture isolate, mai trasferite in produzione.
- Aggiunta configurazione ABE con provenienza per comune/zona e disponibilità.
  Estrazione locale verificata su una pagina pubblica; attivazione e acquisizione
  Hermes della seconda fonte da verificare dopo il deploy.

- Seconda fonte verificata sul server: otto link nel catalogo e 20 immagini
  estratte dal DOM dinamico. Primo ciclo Hermes sulle due fonti completato:
  tre nuovi immobili, zero errori, uno compatibile; due richiedono correzione
  dell'estrattore di località prima di poter essere valutati nei criteri.
- Collaudo autenticato live: schede e immagini, priorità, scenario economico
  calcolato senza salvare ipotesi di prova, export Word valido. Nove endpoint
  HTTP 200 e programma a sei ore confermato.
- Dopo le correzioni: 378 test Python passati nella suite; il solo test Chromium
  richiedeva l'apertura di una porta localhost vietata dalla sandbox ed è passato
  con l'esecuzione autorizzata (379 complessivi). Quattro integrazioni PostgreSQL
  restano saltate. Il refresh dei campi essenziali e le intestazioni alternative
  hanno regressioni dedicate.
