# Verifica del 19 settembre 2026

Base Git: `5344079f67fdcfb3b55ce04f1fe551b0703b97d4`.
Modifiche locali: branch `codex/live-setup`. Deployment non effettuato.

## Modifiche

- Rimossi i residui demo dal frontend e `SEED_DEMO` dal template ambiente.
- Aggiunte al template le opzioni PostgreSQL, worker, immagini e Regolo senza segreti.
- Semplificato il testo del workspace privato nelle impostazioni.
- Corretto il pannello filtri avanzati che si richiudeva dopo il cambio valuta:
  lo stato viene letto prima del render e i toggle di nodi rimossi vengono ignorati.
- Aggiunto `ORACLE_SETUP_PROMPT.md`, con configurazione e collaudo completi.

## Risultati locali

| Verifica | Esito |
| --- | --- |
| pytest | PASS: 303 test; 4 skip PostgreSQL; un warning dipendenza Starlette/AnyIO |
| Sintassi frontend | PASS: 14 moduli |
| Mappa | PASS: 8 invarianti |
| Catalogo JS | PASS: 7 test |
| Processi API/worker | PASS: 7 controlli, incluso lock esclusivo e riavvio |
| UI in Chromium/Helium | PASS: 18 scenari, desktop/mobile, tema scuro, zero errori JS |
| PostgreSQL | NOT RUN: nessun TEST_DATABASE_URL usa-e-getta |
| Regolo | PASS: catalogo autenticato e classificazione con adapter Vedra, qwen3.8-27b; 281 token input, 1931 output |
| Hermes Oracle | NOT RUN: nessuna sessione Oracle o connessione SSH disponibile nel task |
| Vercel/Supabase | BLOCKED: creazione Supabase rifiutata per limite di due progetti gratuiti; nessun deployment Vercel |
| Acquisizione esterna | Ricognizione manuale di due schede reali; raccolta periodica non attivata |

I test UI e dei processi usano dati sintetici in un database temporaneo. Provano
il codice applicativo, non una ricerca immobiliare live. Il test UI iniziale aveva
rilevato la regressione dei filtri; dopo la correzione tutti i 18 scenari sono passati.
Gli screenshot popolati del collaudo non rappresentano immobili acquisiti online.

Il catalogo Regolo autenticato include `qwen3.8-27b`; la classificazione ha
restituito JSON valido e una citazione verificata. Le tariffe non sono state verificate.
Il test usa un testo sintetico e non dimostra ancora la connessione Hermes remota.
Il prompt riporta percorsi Hermes provenienti dal precedente task Oracle, da
riverificare sulla VM. Non sono prove dello stato corrente del servizio.

## Dati necessari per completare il live

- Uno slot Supabase disponibile oppure scelta di PostgreSQL sulla VM Oracle.
  Il connettore stimava costo zero, ma la creazione è stata rifiutata per quota.
- Accesso attuale alla VM Oracle e dominio HTTPS dell'API.
- Fonte/feed/CSV con riuso compatibile. Milano, residenziale in vendita, budget
  500.000–600.000 EUR sono già definiti; criteri in examples/milano-500-600k.criteria.json.
- Login Oracle: il browser Codex è aperto sulla tenancy francescogiannicola1,
  ma richiede autenticazione. Nessuna chiave SSH locale trovata.

Le credenziali dell'allegato non sono state inserite nei sorgenti o nel pacchetto.


## Intervallo di budget

Il criterio min_price è stato aggiunto con default zero, compatibile con le ricerche
precedenti. Il filtro include entrambi gli estremi e rifiuta minimo > massimo.
Sette test coprono i confini, il prezzo mancante e la compatibilità precedente.
Il collaudo browser verifica anche il salvataggio di 500.000–600.000 EUR.

## Ricognizione fonti

Due schede PropertyRE sono state lette il 19 settembre 2026. Le condizioni pubbliche
https://www.propertyre.it/info-legali.asp limitano la riproduzione a finalità
informative non commerciali: nessun connettore ricorrente attivato, nessuna foto o
scheda copiata nel repository. La ricognizione locale rimane negli artefatti esclusi
sia da Git sia dallo ZIP. Non è una prova di disponibilità attuale degli immobili.
