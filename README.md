# Vedra · Real Estate Intelligence

**Versione 0.4.0.** Workspace operativo per raccogliere annunci da fonti configurate,
confrontare dati omogenei e gestire lo screening del team. Un’installazione nuova parte vuota, pronta per collegare le fonti. Le fixture sintetiche sono
isolate nei test e non entrano nei bundle Vercel o Docker.

## Avvio locale

Richiede Python 3.11+. Non richiede Node per funzionare, una GPU o un account AI.

```bash
bash start.sh
# Windows: powershell -ExecutionPolicy Bypass -File start.ps1
```

Apri `http://127.0.0.1:8000`. Il setup genera `.env` e mostra la password iniziale una
sola volta. Conserva `.env` e `data/` fuori da GitHub. Gli account non sono pubblici:
l’amministratore aggiunge analisti e lettori dalle impostazioni.

## Percorso effettivo dei dati

1. Configura una fonte HTML autorizzata e il relativo dominio in `LIVE_ALLOWED_DOMAINS`,
   oppure importa il CSV del cliente. I tracciati scaricabili contengono solo le intestazioni.
2. Usa **Test** sulla fonte: una ricerca e al massimo un annuncio, con campi mancanti
   e risultato persistente. Gli URL con `{city}` richiedono un comune di test esplicito.
3. Crea un agente con zona, criteri e fonti. **Esegui ora** accoda un vero job; una
   frequenza maggiore di zero abilita gli avvii periodici.
4. Usa **Diagnostica** sull’agente: verifica configurazione, fonti e presenza del worker
   senza inviare richieste esterne. Controlla poi log, salute delle fonti, qualità e risultati. Un blocco attiva una pausa;
   non viene aggirato e non viene presentato come assenza di immobili.
5. Importa benchmark verificabili. Score e delta restano assenti quando i dati non sono
   confrontabili. Il ranking non è una probabilità di profitto.

Il collector implementa HTML/JSON-LD/CSS, sitemap e rendering browser opzionale.
**Non sono inclusi connettori già certificati per Idealista, Immobiliare.it o Casa.it.**
Un Hermes acceso non concede accesso ai portali né sostituisce la configurazione delle fonti.

## Cosa comprende

| Area | Funzioni |
|---|---|
| Dashboard | Panoramica live, ricerca, tabella/schede, coordinate dichiarate, tema scuro, mobile e stati vuoti. |
| Origination | Fonti verificabili, job persistenti, deduplica per annuncio, revisione dei duplicati, snapshot e storico osservazioni. |
| Insight | Nuovi nell’archivio, dati da ricontrollare, ribassi con contesto storico coerente, fonti in errore, verifiche scadute e segmenti comparabili. |
| Screening | Filtri in codice, benchmark compatibili, scoring spiegabile, classificazione AI opzionale con citazioni. |
| Archivio | Ricerca server-side completa, paginazione, filtri economici e viste operative; selezione tra pagine fino a 100 annunci. |
| Evidenze | Cronologia campo per campo sulle nuove osservazioni, confronto con la rilevazione precedente, copertura storica esplicita. |
| Team | Revisioni multiple atomiche con controllo versione, motivazione per scarto; pipeline, responsabili, checklist, scadenze, note, shortlist, viste personali e controllo delle modifiche simultanee. |
| Scenari | Ipotesi esplicite di acquisto, lavori, vendita e mantenimento; pareggio, ROI semplice e sensibilità. Non una previsione. |
| Delivery | CSV/XLSX/DOCX, inbox e coda SMTP opzionale. |
| Operazioni | API e worker separabili, heartbeat condiviso, lock esclusivo, timeout, recupero dopo riavvio e controlli diagnostici. |

## Archivio e revisione quotidiana

**Opportunità** interroga tutto il database, non solo i primi 2.000 record caricati dalla
panoramica. Puoi filtrare per fonte, comune, strategia, valuta, intervalli di prezzo e
superficie. Per i prezzi è obbligatoria una valuta: non confrontiamo importi EUR e USD
come se fossero equivalenti. Campi mancanti non soddisfano un intervallo numerico.

Viste rapide: nuovi negli ultimi 7 giorni, da aggiornare (oltre 7 giorni dall’ultima
rilevazione), senza benchmark, revisioni scadute e deal da assegnare. Non indicano
vendite, disponibilità certa o profitto. Le viste personali conservano anche questi filtri.

La selezione rimane tra pagine e filtri, con limite di 100 annunci. **Aggiorna stato**
mostra la selezione corrente prima della conferma: un conflitto di versione annulla
l’intero aggiornamento. Responsabile, checklist e scadenza non vengono sovrascritti.
Per scartare è obbligatoria una motivazione; le modifiche entrano nel registro audit.

CSV/Excel senza selezione esportano la vista filtrata, non solo la pagina visibile.
Oltre 2.000 righe il server chiede di restringere i filtri: nessun file viene troncato
silenziosamente. Panoramica, pipeline e alcune funzioni legacy restano una vista
operativa limitata e dichiarata; la ricerca completa è in Opportunità.

La cronologia dei campi è raccolta **dalla 0.4 in poi**. Le osservazioni precedenti
restano disponibili, ma i campi mancanti non vengono ricostruiti con i valori attuali.
[Dettagli dei contratti](docs/CATALOG.md) · [Aggiornamento](docs/UPGRADE.md).

## Vercel + Supabase + VPS

```text
Browser → Vercel (solo frontend statico)
                  ↓ /api/* stesso dominio
             API Vedra sulla VPS
                  ↓
          PostgreSQL privato Supabase
                  ↑
             Worker sulla VPS → fonti autorizzate
                  ↓
           provider AI / Hermes opzionale
```

La VPS ospita **anche API e worker**, non soltanto Hermes. Il frontend non riceve
password PostgreSQL, chiavi AI o credenziali Supabase privilegiate. Questa release
usa l’autenticazione Vedra esistente, non Supabase Auth.

Procedura completa: **[docs/CLOUD.md](docs/CLOUD.md)**.
Prompt operativo Oracle/Hermes: **[docs/ORACLE_SETUP_PROMPT.md](docs/ORACLE_SETUP_PROMPT.md)**. Esempi inclusi:
`vercel.json`, `compose.cloud.yaml`, `deploy/supabase.sql`, reverse proxy e systemd.

È una distribuzione dedicata per cliente. Non dichiarare disponibili registrazione
pubblica, pagamenti ricorrenti o isolamento multi-tenant condiviso: non sono implementati.

## Scout: l’agente che naviga le fonti

Scout è l’agente di ricerca di Vedra, dentro il worker: nessun servizio esterno da gestire.
Apre ogni fonte con il browser come farebbe una persona (stesso dominio, robots.txt, ritmo
lento, nessun aggiramento), poi il modello legge la pagina: sceglie gli annunci, le sezioni da
aprire e la pagina successiva seguendo le istruzioni della ricerca, e compila i dati della scheda
che il parser non trova (prezzo nella descrizione, catasto, cambio d’uso, broker, “venduto”).
Ogni valore deve comparire nel testo della pagina: quello che manca resta vuoto.

```bash
# .env (solo locale, mai su GitHub)
AI_API_BASE_URL=https://api.regolo.ai/v1
AI_API_KEY=...
AI_MODEL=qwen3.8-27b
BROWSER_ENABLED=true
LIVE_ALLOWED_DOMAINS=www.tecnocasa.it,www.gabetti.it,...
```

In **Fonti → Collega fonte** scegli una rete di agenzie pronta; in **Ricerche** seleziona il
motore Scout, scrivi le istruzioni (“solo Milano centro sopra 4 M, annota il broker”) e la
frequenza. Verificato dal vivo su Tecnocasa, Gabetti e ABE Immobiliare: circa 2–3 centesimi di
euro per ricerca con qwen3.8-27b. immobiliare.it, idealista e casa.it rispondono 403 ai browser
automatizzati: la ricerca lo segnala e prosegue sulle altre fonti. Hermes resta disponibile solo
come motore legacy se già configurato. Stima dei consumi: [docs/COSTI_ESERCIZIO.md](docs/COSTI_ESERCIZIO.md).

La pagina **Broker** raggruppa gli inserzionisti di tutte le fonti per telefono o email, con
valore degli annunci, zone e dichiarazioni di vendita diretta o esclusiva.

## Aggiornamento e dati precedenti

Prima interrompi le scritture e fai il backup. Mantieni `.git`, `.env` e `data/`;
aggiorna i sorgenti e le dipendenze. La migrazione dello schema è idempotente.

```bash
python scripts/purge_demo.py              # inventario, non cancella nulla
python scripts/purge_demo.py --apply --writes-stopped --backup-confirmed
```

I vecchi record sintetici sono esclusi dalle API; gli agenti che li usavano vengono
sospesi in migrazione. La pulizia esplicita li rimuove mantenendo intatti i dati reali.
Per il passaggio a PostgreSQL, `scripts/migrate_sqlite.py` copia verso uno schema vuoto,
non modifica il file sorgente e invalida le vecchie sessioni. [Guida upgrade](docs/UPGRADE.md).

## Criteri personalizzati ed Excel

Ogni agente può combinare filtri numerici con istruzioni qualitative, ad esempio
«solo immobili con cambio d’uso dichiarato». Hermes o AI verticale restituisce
un esito, una motivazione e citazioni controllate sul testo. Un dato mancante resta
da verificare; cambiare prompt o annuncio invalida il vecchio esito. Il motore a
regole non interpreta istruzioni libere.

Excel è disponibile per la selezione e per il singolo immobile. Il foglio iniziale
riunisce criteri, verifiche e riferimenti; fogli separati conservano comparabili,
istruzioni AI e storico osservato. I prezzi richiesti di immobili da ristrutturare,
ristrutturati e nuovi rimangono distinti dalle quotazioni OMI.
[Vedi il flusso e i limiti](docs/FEATURE_WORKLIST.md).

## Verifica

```bash
python -m pip install -r requirements-dev.txt
pytest -q
node scripts/check_frontend.mjs
node scripts/test_map.mjs
node scripts/test_catalog.mjs
node scripts/test_signals_ui.mjs
node scripts/test_run_ui.mjs
python scripts/test_worker_processes.py
python -m playwright install chromium
python scripts/test_ui.py
```

PostgreSQL ha test d’integrazione separati con `TEST_DATABASE_URL` e un servizio
Postgres 16 nella CI. L’assenza di questo parametro produce uno **skip dichiarato**,
non un test superato. [TEST_REPORT.md](TEST_REPORT.md) distingue ciò che è stato
eseguito in questa consegna da ciò che richiede gli accessi del cliente.

## Struttura

```text
backend/app/           API, servizi, parser, schema e driver database
backend/tests/         test e fixture isolate
frontend/src/          componenti condivisi e viste senza build runtime
frontend/public/       asset statici e tracciati vuoti
hermes/                profilo, MCP e skills circoscritte
scripts/               avvio, verifica, migrazione, packaging e PR
deploy/               provisioning e processi VPS
docs/                 architettura, deployment, collaudo e limiti
```

Design: Inter configurato via CSS, palette blu/navy, componenti riutilizzati e
interazioni ispirate ai principi di Emil Kowalski. Nessun file di font incluso;
in assenza di rete viene usato il font di sistema. [Standard UI](docs/DESIGN.md).

## Pubblicazione su GitHub

La patch della release è basata su `f1a47fc1c5873992ab6cbb99e56770dfc141d2dc`.
Da questa cartella estratta, con un clone pulito e GitHub CLI autenticata:

```bash
python scripts/publish_pr.py --repo /percorso/al/clone/vedra-real-estate \
  --patch /percorso/Vedra_0.4.0.patch --merge
```

La pubblicazione crea un nuovo branch e una PR; il merge è condizionato ai check
`tests` e `postgres` entrambi verdi e al rispetto delle revisioni. Nessun bypass
o force push. Senza `--merge` apre soltanto la PR. Non applicare la patch sopra una
copia della stessa release: usa il clone pulito. Vedi `docs/PR.md`.

## Flusso decisionale locale

La pagina **Oggi** raccoglie gli immobili selezionati e dichiarati pubblicati, con
recapiti acquisiti, motivo della selezione e richiami. Gli esiti dei contatti sono
un registro del team separato dalle dichiarazioni della fonte.

Le ricerche accettano criteri qualitativi per riga e, con Hermes online, istruzioni
di navigazione e pagine iniziali specifiche sul dominio delle fonti selezionate.
La scheda mostra la verifica dei criteri; l’esecuzione conserva istruzioni e pagine
consultate. L’Excel include selezione, riferimenti, comparabili, criteri, storico e
contatti e confronto tra fonti dello stesso asset. I campioni mostrano fonti, date
e dispersione; i dati discordanti richiedono verifica. Vedi [funzioni e limiti](docs/FEATURE_WORKLIST.md).


Le nuove ricerche possono escludere prezzi in linea e confronti mancanti e cercare
contatti diretti dichiarati. Gli scenari salvabili mostrano ROI obiettivo, tetto
d’acquisto e stress combinato su prezzo, lavori e durata. L’Excel esporta gli stessi
input e risultati visibili nella piattaforma. Nessuna probabilità di profitto è stimata.
