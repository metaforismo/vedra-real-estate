# Copertura del brief

| Requisito | Presente nella preview | Limite |
|---|---|---|
| Dashboard accessibile | UI completa, sessioni e ruoli | URL pubblico da distribuire sul proprio server |
| Ricerche per zona | Comune, filtri, fonti, frequenza | Non ricerca per poligono/raggio o provincia aggregata |
| Discovery & ingestion | HTML/JSON-LD/CSS, browser opzionale, CSV/HTML import | Connettore generico, non copertura verificata dei portali elencati nel brief |
| Normalizzazione | Schema, campi nulli, hash, evidenze | JSON proprietari/PDF richiedono adapter separati |
| Deduplica | Esatta per fonte/ID + candidati cross-source | Nessun matching immagini o merge probabilistico automatico |
| Classificazione strategica | Regole locali oppure Hermes con quote | Non verifica urbanistica, non estrazione libera di numeri via LLM |
| Benchmark | CSV normalizzato, matching omogeneo, delta e formula | Nessun download OMI, geocoding/assegnazione zona o transati live |
| Monitoraggio | Coda persistente, timer, run manuale, stop, log | Singolo worker; no garanzia real-time o SLA |
| Memoria | Configurazioni, osservazioni e stato nel DB | Non una conversazione LLM illimitata |
| Qualità | Completezza del campione, errori delle fonti | Non accuratezza o percentuale di copertura del mercato |
| Reporting | CSV/XLSX/DOCX, note e shortlist | Nessun invio email o memorandum di investimento certificato |
| Urbanistica/predictive | Non implementato | Fuori dalla preview |
| Multi-agent | Skills di discovery e classificazione in un profilo Hermes | Non uno swarm autonomo, nessun profilo per ogni ricerca |

**Criterio di accettazione della preview dati:** un campione reale da una fonte consentita, campi e relative assenze verificati manualmente, nessuna sostituzione con dati sintetici, confronto prezzi usato solo quando il benchmark è valido. Questo criterio va eseguito sull’infrastruttura e sulle fonti del cliente: non è stato certificato dal pacchetto generato offline.
