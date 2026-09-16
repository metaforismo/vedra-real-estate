# Copertura del brief

| Requisito | Presente in 0.3 | Limite |
|---|---|---|
| Dashboard accessibile | UI completa, sessioni e ruoli | Build Vercel + API VPS predisposte; deployment da collaudare |
| Ricerche per zona | Comune, filtri, fonti, frequenza | Non ricerca per poligono/raggio o provincia aggregata |
| Discovery & ingestion | HTML/JSON-LD/CSS/sitemap, browser opzionale, CSV/HTML import | Connettore e probe generici, non copertura verificata dei portali del brief |
| Normalizzazione | Schema, campi nulli, hash, evidenze | JSON proprietari/PDF richiedono adapter separati |
| Deduplica | Esatta per fonte/ID + candidati cross-source | Revisione manuale; nessun matching immagini automatico |
| Classificazione strategica | Regole locali, provider diretto oppure Hermes con quote | Non verifica urbanistica, non estrazione libera di numeri via LLM |
| Benchmark | CSV normalizzato, matching omogeneo, delta e formula | Nessun download OMI, geocoding/assegnazione zona o transati live |
| Monitoraggio | Coda persistente, timer, run manuale, stop, log | Singolo worker; no garanzia real-time o SLA |
| Memoria | Configurazioni, osservazioni e stato nel DB | Non una conversazione LLM illimitata |
| Qualità | Completezza del campione, errori delle fonti | Non accuratezza o percentuale di copertura del mercato |
| Reporting | CSV/XLSX/DOCX, note e shortlist | SMTP opzionale con outbox; nessun memorandum certificato |
| Revisione e scenari | Pipeline, owner, checklist, scadenza, scenari salvabili | Ipotesi utente, nessuna valutazione di rivendita automatica |
| SaaS | Istanza dedicata per cliente | Nessun billing/provisioning multi-tenant |
| Urbanistica/predictive | Non implementato | Fuori dalla preview |
| Multi-agent | Skills di discovery e classificazione in un profilo Hermes | Non uno swarm autonomo, nessun profilo per ogni ricerca |

**Criterio di accettazione della preview dati:** un campione reale da una fonte consentita, campi e relative assenze verificati manualmente, nessuna sostituzione con dati sintetici, confronto prezzi usato solo quando il benchmark è valido. Questo criterio va eseguito sull’infrastruttura e sulle fonti del cliente: non è stato certificato dal pacchetto generato offline.

Insight aggregati e fotografie servono solo dati acquisiti/importati; non sono
una fonte di mercato aggiuntiva. PostgreSQL è implementato con test CI dedicati,
non presentato come una connessione Supabase già provata per il cliente.
