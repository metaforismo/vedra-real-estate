# Changelog

## 0.4.0 · 2026-09-18

Archivio server-side paginato, filtri coerenti di valuta/prezzo/superficie/fonte,
viste operative e ricerche oltre il campione della dashboard. Export filtrati e
selezionati senza troncamenti silenziosi. Revisione multipla fino a 100 annunci,
concorrenza ottimistica, note e audit atomici. Migrazione v4: indice strategie e
snapshot dei campi osservati; nessuna retro-compilazione della storia. Cronologia
paginata e contesto delle variazioni. Diagnostica agente senza chiamate esterne,
invalidazione dei test fonte quando cambia configurazione. Tastiera, selezione tra
pagine, stati caricamento/errore, cancellazione e ignoramento delle risposte obsolete.
Corretto .env.example effettivamente presente su GitHub, ancora della prima preview.


## 0.3.0 · 2026-09-16

- Elimina catalogo e controlli demo dall’app; fixture isolate nei test.
- Aggiunge driver PostgreSQL/Supabase, schema privato, migrazione e pulizia legacy esplicita.
- Separa API e worker, con heartbeat condiviso e lock esclusivo locale o PostgreSQL.
- Build frontend Vercel, esempi VPS, diagnosi della fonte e proxy immagini autorizzate.
- Insight su freschezza, riduzioni omogenee, scadenze e campioni comparabili; nuova panoramica.
- Rafforza skills Hermes, configurazione e documentazione; test di processi separati e CI PostgreSQL.
- I limiti effettivamente verificati sono in TEST_REPORT.md.


## 0.2.0 · 2026-09-16

Dashboard blu/navy e Inter remoto opzionale, dataset reale vuoto per default,
pipeline con owner/checklist/conflitti, scenari economici salvati, comparabili
interni omogenei, revisione duplicati, viste personali, inbox e outbox SMTP.
Provider Chat Completions configurabile con Regolo solo esempio locale,
consumi dichiarati, limiti run/analisi, nessun fallback AI silenzioso.
Hermes opzionale via tre tool MCP e capability scoped, controllo toolset effettivo.
Migrazione v1→v2, lock OS, cache dettagli, sitemap di URL, cooldown fonti,
setup/manuale e start scripts, documentazione di upgrade e collaudo.

Non inclusi: portali live prevalidati, OMI automatico, CTU/urbanistica,
previsioni, multi-tenancy condivisa, billing o deployment pubblico.


## 0.1.0 · 2026-09-15

Prima preview: dashboard italiana responsive, temi chiaro/scuro, sessioni e ruoli;
agenti persistenti, coda singola, programmazione, pausa e log; acquisizione HTML/
JSON-LD con CSS configurabile e browser opzionale; import CSV/HTML e benchmark;
storico osservazioni, segnalazione duplicati, scoring spiegabile e qualità dati;
confronto fino a tre immobili, preferiti, note, shortlist, CSV/XLSX/DOCX;
adapter Hermes Runs API, due skills e bridge autenticato; preflight senza LLM,
classificazione incrementale con evidenze immutabili e task a blocchi da 10;
script di setup, Docker, CI, test e documentazione.

Non inclusi: connettori garantiti per portali specifici, download OMI automatico,
urbanistica, CTU/OCR, immagini per entity resolution, previsioni, rendimenti,
notifiche email, multitenancy o deployment pubblico già effettuato.
