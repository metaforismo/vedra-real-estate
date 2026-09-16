# Vedra · Real Estate Workspace

**Versione 0.2.0 · workspace operativo a istanza dedicata.**

Ricerche programmate, acquisizione controllata, storico degli annunci, classificazione,
screening e revisione del team. Backend Python, dashboard italiana responsive in
JavaScript nativo. Nessuna build Node necessaria per l'avvio, nessuna GPU richiesta.

![Dashboard Vedra su dati sintetici di QA](docs/screenshots/dashboard.png)

Lo screenshot usa fixture sintetiche etichettate. **L'installazione normale parte
vuota, sul dataset reale.** Non vengono inseriti immobili, metriche o notifiche
fittizie. Il software è eseguibile; l'accesso alla fonte e al provider effettivo
va configurato e provato nel proprio ambiente. Non include integrazioni collaudate
sui grandi portali immobiliari né un abbonamento a dati/AI.

## Avvio

Python 3.11 o successivo e rete per installare le dipendenze. Su macOS/Linux:

```bash
bash start.sh
```

Apri `http://127.0.0.1:8000`. Il primo setup stampa email e password generate
localmente e salva `.env` con permessi restrittivi. Gli avvii successivi non
sovrascrivono configurazione, credenziali o dati. Lo script verifica/installa le
dipendenze nel virtualenv a ogni avvio. Per un servizio permanente avvia direttamente
`.venv/bin/python scripts/run.py` dopo l'installazione.

Equivalente manuale:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/setup.py
python scripts/run.py
```

Windows PowerShell: `./start.ps1` oppure i medesimi comandi usando
`.venv/Scripts/python.exe`. Nessun bypass della policy PowerShell è richiesto;
quando gli script sono disabilitati, usa i comandi Python manuali.

**Aggiornamento da 0.1:** leggi [UPGRADE](docs/UPGRADE.md) prima di sostituire i file.
Non eliminare `.env`, `data/` o il database. Ferma il processo, fai un backup,
aggiorna i sorgenti e riavvia: la migrazione dello schema avviene all'avvio.

## Primo agente con dati reali

1. Nel `.env` imposta `LIVE_ALLOWED_DOMAINS` ai domini esatti delle fonti per cui
   hai titolo di accesso/riuso. Riavvia Vedra. Non usare wildcard o domini privati.
2. In **Fonti → Aggiungi fonte**, configura URL ricerca, selettore dei link,
   sottostringa URL degli annunci, eventuale paginazione e selettori dei campi.
   Il connettore prova JSON-LD e usa i selettori configurati. Puoi scegliere una
   sitemap di URL in alternativa alla pagina di ricerca.
3. Esegui **Verifica fonte** e confronta i campi estratti con la pagina originale.
   Un errore, un blocco o zero link non vengono presentati come mercato vuoto.
4. Crea un agente sul comune e sulla fonte, inizialmente manuale e con 5 annunci.
   **Esegui ora**, controlla i risultati, le fonti dei valori e il registro della run.
5. Dopo una prova riuscita abilita una frequenza di almeno 15 minuti. Le pagine
   degli annunci hanno una frequenza di aggiornamento separata (default 24 ore).
   Il sistema non rilegge ogni dettaglio a ogni controllo.

In alternativa importa CSV/HTML già acquisiti legittimamente. Un agente associato
a un'importazione classifica i record disponibili: **non trasforma un CSV in un
monitoraggio online**. Percorso completo e limiti in [DATA](docs/DATA.md) e
[LOCAL_TEST](docs/LOCAL_TEST.md).

## AI: tre modalità, senza dipendenza obbligatoria da un provider

| Runtime nella UI | Cosa fa |
|---|---|
| **Regole locali** | Acquisizione, screening e classificazione deterministica. Nessuna chiamata AI. |
| **AI configurata** | Classificazione semantica tramite Chat Completions compatibile, soltanto sugli annunci idonei nuovi/cambiati o non ancora analizzati. |
| **Hermes** | Runtime opzionale, profilo dedicato, tre tool MCP ammessi, evidenze immutabili e capability limitata alla run. |

Il codice gestisce acquisizione, deduplica, database, calcoli e pianificazione.
Il modello interpreta testo e propone strategie con citazioni testuali; non
modifica prezzi, superfici, formule o permessi. Le sue sintesi rimangono una
lettura preliminare da verificare, non una perizia.

Per **AI configurata**, valorizza sul server:

```dotenv
AI_API_BASE_URL=https://provider.example/v1
AI_API_KEY=
AI_MODEL=
AI_RESPONSE_FORMAT=json_object
AI_REASONING_EFFORT=
AI_MAX_OUTPUT_TOKENS=2000
AI_MAX_ANALYSES_PER_RUN=30
RUN_TIMEOUT_SECONDS=900
```

Endpoint, modello e chiave vuoti disabilitano la modalità. I provider devono
supportare il contratto descritto in [AI](docs/AI.md). Un errore non produce un
fallback silenzioso presentato come risultato AI.

**Regolo e `qwen3.8-27b` sono soltanto un esempio di test locale**:
[examples/regolo.local.env.example](examples/regolo.local.env.example).
Non sono i default di Vedra. Nessuna chiave reale è inclusa.

```bash
# Solo controllo configurazione: nessuna richiesta al modello
python scripts/check_ai.py
# Un test sintetico esplicito; può comportare addebiti del provider
python scripts/check_ai.py --live --accept-cost
```

Per Hermes: [configurazione e modello di isolamento](docs/HERMES.md).

## Funzioni incluse

**Dashboard:** panoramica blu/navy, Inter con fallback di sistema, temi chiaro/scuro,
layout mobile, ricerca, filtri e viste personali salvate. Metriche ricavate dal database,
mappa schematica offline delle coordinate disponibili, top risultati e attività.
La mappa non è catastale, non geocodifica e non inventa posizioni.

**Acquisizione e agenti:** HTML/JSON-LD/CSS, sitemap di URL, rendering browser opzionale,
import CSV/HTML, avvio manuale, timer, pausa, annullamento, coda persistente, log,
cache temporale dei dettagli, storico prezzi/snapshot e stato di salute delle fonti.

**Screening e decisioni:** filtri per comune, prezzo, superficie, tipologia e strategia;
benchmark importati e omogenei, score con formula visibile; comparabili interni,
revisione dei duplicati senza distruggere le fonti; preferiti, confronto e note.
La pipeline aggiunge responsabile, scadenza interna, sette fasi e checklist umana
con protezione dalle sovrascritture simultanee.

**Scenari economici:** ipotesi utente di acquisto, lavori, costi, imprevisti, gestione,
durata e rivendita. Capitale impiegato, risultato, ROI semplice non annualizzato,
pareggio e sensibilità. Salvataggio e riapertura. Nessun debito, previsione di
rivendita o imposta aggiuntiva non inserita nei costi.

**Operatività:** inbox persistente e lettura personale, email SMTP opzionali con
outbox e tentativi limitati, diagnostica, consumi AI dichiarati dal provider,
registro modifiche, cambio password e revoca delle altre sessioni.

**Consegna:** esportazioni CSV, XLSX e DOCX, account admin/analyst/viewer,
Docker Compose e systemd di esempio, script di backup, CI e test.

## Limiti deliberati e verifiche

- Nessun scraping garantito di Idealista/Immobiliare/Casa/PVP; connettori generici
  da calibrare sulle fonti autorizzate. Nessun bypass di CAPTCHA, login o anti-bot.
- Nessun download OMI automatico. Un confronto senza metadati compatibili resta
  indisponibile. Prezzi richiesti non sono prezzi di transazione.
- Nessuna acquisizione CTU/PDF, analisi PGT/NTA, autorizzazione al cambio d'uso,
  previsione di vendita/exit price o riconoscimento visuale avanzato dei duplicati.
- Nessuna galleria fotografica remota automatica: i riferimenti immagini rimangono
  nei dati, senza caricare contenuti di terzi nel browser del cliente.
- Un processo/worker per database. Il lock evita la concorrenza accidentale; non è
  una coda distribuita. Retention e cancellazione massiva non automatizzate.
- Account nello stesso workspace condividono gli immobili. Viste e lettura inbox
  sono personali. **Questa release non è un SaaS multi-tenant self-service.**
  Separare database, segreti e runtime per cliente: [SAAS](docs/SAAS.md).
- Test qui su fixture, trasporto HTTP simulato per i provider e backend locale.
  Regolo/Hermes/portali live, SMTP esterno, Docker e deployment HTTPS non verificati.
  Vedi [TEST_REPORT](TEST_REPORT.md) per comandi e risultati esatti.

## Sviluppo e verifiche

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
node scripts/check_frontend.mjs
python -m playwright install chromium
python scripts/test_ui.py
```

Node serve solo al controllo sintattico JavaScript. Su Linux i test browser possono
richiedere `python -m playwright install --with-deps chromium`. `--relay` nel runner
UI è riservato ad ambienti QA con navigazione locale bloccata; non viene usato
dall'applicazione e non sostituisce la prova diretta sul browser del cliente.

Struttura:

```text
backend/app/connectors/     rete controllata, parser e sitemap
backend/app/services/       workflow, calcoli, provider, persistenza, email
backend/app/routes/         API operative
backend/tests/              regressioni, contratti, migrazione e scenari
frontend/src/               moduli ES e design system locale
hermes/mcp/                 server stdio a tre tool
hermes/skills/              procedure verticali
scripts/                   setup, run, backup, QA e packaging
```

Gli snapshot dei dati non sono la memoria conversazionale del modello. Una run
ha configurazione e task immutabili; le modifiche ai criteri valgono dalla run
successiva. Le esecuzioni interrotte sono marcate tali al riavvio e non vengono
spacciate per completate.

## Caricare su GitHub

Copia il **contenuto** della cartella `vedra-real-estate` nella radice della repo,
compresi `.github`, `.gitignore` e `.env.example`. Conserva separatamente `.env` e
`data/`; non caricarli. Lo ZIP contiene tutto il sorgente, non un elenco di patch.
`MANIFEST.sha256` consente di verificare i file. Per rigenerare il pacchetto:

```bash
python scripts/package.py --output dist/Vedra_0.2.0_Complete.zip
```

Base della release: commit `ce6e3d96161d1800d06d842853f07aaffb52d780` della repo
`metaforismo/vedra-real-estate`. Lo ZIP non modifica da solo il repository remoto.
