# Vedra · Real Estate Intelligence

**Versione 0.3.0.** Workspace operativo per raccogliere annunci da fonti configurate,
confrontare dati omogenei e gestire lo screening del team. Nessun catalogo dimostrativo
nell’applicazione: un’installazione nuova parte vuota. Le fixture sintetiche sono
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
4. Controlla log, salute delle fonti, qualità e risultati. Un blocco attiva una pausa;
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
| Team | Pipeline, responsabili, checklist, scadenze, note, shortlist, viste personali e controllo delle modifiche simultanee. |
| Scenari | Ipotesi esplicite di acquisto, lavori, vendita e mantenimento; pareggio, ROI semplice e sensibilità. Non una previsione. |
| Delivery | CSV/XLSX/DOCX, inbox e coda SMTP opzionale. |
| Operazioni | API e worker separabili, heartbeat condiviso, lock esclusivo, timeout, recupero dopo riavvio e controlli diagnostici. |

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

Procedura completa: **[docs/CLOUD.md](docs/CLOUD.md)**. Esempi inclusi:
`vercel.json`, `compose.cloud.yaml`, `deploy/supabase.sql`, reverse proxy e systemd.

È una distribuzione dedicata per cliente. Non dichiarare disponibili registrazione
pubblica, pagamenti ricorrenti o isolamento multi-tenant condiviso: non sono implementati.

## AI e Hermes

Il runtime `local` usa regole, senza spacciarle per AI. `llm` usa un endpoint Chat
Completions configurabile; `hermes` usa un profilo dedicato con soli tre tool MCP.
Regolo/Qwen è un esempio locale facoltativo, non una dipendenza del prodotto.

```bash
python scripts/check_ai.py                 # configurazione, nessuna chiamata pagata
python scripts/check_ai.py --live --accept-cost
```

Credenziali solo in `.env`. Le skills sono in `hermes/skills/`; configurazione e
permessi in [docs/HERMES.md](docs/HERMES.md). La pianificazione appartiene a Vedra:
non aggiungere un secondo cron Hermes sullo stesso agente.

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

## Verifica

```bash
python -m pip install -r requirements-dev.txt
pytest -q
node scripts/check_frontend.mjs
node scripts/test_map.mjs
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

La patch della release è basata su `6d4325bdfe0431df8b6dc261908cf114d8b8536f`.
Da questa cartella estratta, con un clone pulito e GitHub CLI autenticata:

```bash
python scripts/publish_pr.py --repo /percorso/al/clone/vedra-real-estate \
  --patch /percorso/Vedra_0.3.0.patch --merge
```

La pubblicazione crea un nuovo branch e una PR; il merge è condizionato ai check
`tests` e `postgres` entrambi verdi e al rispetto delle revisioni. Nessun bypass
o force push. Senza `--merge` apre soltanto la PR. Non applicare la patch sopra una
copia della stessa release: usa il clone pulito. Vedi `docs/PR.md`.
