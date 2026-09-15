# Verifiche della consegna

Data: **15 settembre 2026**. Versione applicativa: **0.1.0 preview**.

## Risultati eseguiti

| Verifica | Risultato |
|---|---|
| `pytest -q` | **107 test passati** |
| Compilazione Python di backend, script e skills | Passata |
| Sintassi dei moduli ES con Node | **6 moduli passati** |
| Percorsi Chromium con backend reale temporaneo | **7 gruppi di verifiche passati, nessun errore JavaScript** |
| Desktop | 1440 × 1080; screenshot dell'app realmente eseguita |
| Mobile | 393 × 852; navigazione e layout senza overflow orizzontale del documento |
| Temi | Chiaro e scuro verificati |
| Word | Export di una scheda demo, rendering a una pagina e controllo visivo |
| Excel | Export di 36 immobili demo, due fogli, controllo formule/cache, rendering e verifica visiva di un campione |

### Copertura automatica

Parser JSON-LD/CSS e normalizzazione; dati assenti, valuta ignota e valori non validi; regole e citazioni testuali; compatibilità e scadenza dei benchmark; formula e score nullo in assenza di dati; importazioni e provenienza; deduplica elementare; storico, note e stato di revisione.

Sessioni, CSRF, autorizzazioni dei ruoli, limiti di richiesta, iniezione di formule nelle esportazioni, configurazioni immutabili delle run, unicità dei job attivi, errori dei connettori, contatori e stati finali, completezza del protocollo bridge, analisi retroattiva degli annunci già raccolti e nessuna chiamata LLM in assenza di task semantici.

Per le richieste esterne: allowlist, indirizzi privati, pinning dell'IP/Host/TLS, redirect, robots, limiti e risposte di blocco sono testati con `httpx.MockTransport`. Questi test non costituiscono una prova di acquisizione da un portale commerciale.

Per Hermes: test dei payload e dei flussi di capabilities, creazione run, polling, arresto, errori, token e consegna dei task. Il gateway è simulato nei test contrattuali; non è stato speso credito modello o eseguita una run su un servizio Hermes reale.

Gli helper sono verificati per setup senza sovrascrittura, permessi del file `.env`, installazione delle skills, protezione del profilo personale, conservazione delle chiavi provider e assenza di token nell'output del configuratore.

### Percorsi browser

1. Login, sessione reale e panoramica.
2. Scheda immobile e persistenza di una nota del team.
3. Selezione, confronto di due asset, filtro comune e vista a schede.
4. Creazione di un nuovo agente, elaborazione della coda reale, log completato, pausa e ripresa.
5. Upload CSV nel form reale e importazione nel database.
6. Qualità dei dati e stato esplicito «Hermes non configurato».
7. Tema scuro e navigazione mobile.

Il browser usa dati sintetici, ma le operazioni attraversano davvero FastAPI, autenticazione, parser e SQLite. Non sono risposte API preregistrate o un prototipo statico.

**Particolarità dell'ambiente di QA:** una policy Chromium dell'ambiente impedisce la navigazione diretta agli URL. È stata usata l'opzione `--relay` dello script: carica l'HTML locale e inoltra richieste/risposte al backend HTTP realmente avviato. Solo questo trasporto di test adatta origin, cookie e CSP. Il codice applicativo mantiene le protezioni originali; autenticazione, CSRF e header sono verificati separatamente nei test API. La normale esecuzione dello script e la CI configurata usano navigazione diretta, senza relay. Questo non equivale a una verifica end-to-end del deployment pubblico con HTTPS.

```bash
pytest -q
node scripts/check_frontend.mjs
python -m compileall -q backend scripts hermes
python scripts/test_ui.py
# Solo per l'ambiente con la limitazione descritta:
python scripts/test_ui.py --chromium /usr/bin/chromium --relay
```

## Ambiente verificato

Linux, Python 3.13.5, Node 22.16.0, Playwright 1.57.0 e Chromium installato dal sistema. Le versioni runtime Python sono riportate in `requirements.txt`. La compatibilità dichiarata parte da Python 3.11; non sono state eseguite matrici su ogni versione Python, macOS o Windows.

## Non eseguito e non garantito

- Installazione Docker/Compose o build dell'immagine: configurazioni fornite, Docker non disponibile in questa sessione.
- Deploy su VPS pubblico, HTTPS, reverse proxy e accesso del cliente.
- Run reale Hermes/provider LLM, latenza e costi di inference.
- Scraping live di Idealista, Immobiliare.it, Casa.it, PVP o altri portali; nessuna copertura di questi siti è dichiarata.
- Ottenimento di licenze o permessi di accesso/riuso; importazione di quotazioni OMI ufficiali.
- Matrice completa di tutte le pagine e browser, pen-test indipendente, carico elevato, alta disponibilità o backup/restore operativo di un workspace cliente.
- Esecuzione remota della GitHub Actions inclusa: la pipeline è predisposta, non già eseguita sul futuro repository dell'utente.

Le immagini in `docs/screenshots/` sono screenshot della preview realmente avviata. I numeri mostrati sono risultati del dataset dimostrativo e **non evidenza di opportunità immobiliari reali**.
