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
