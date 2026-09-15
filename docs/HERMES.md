# Hermes: installazione delle skills e contratto effettivo

## Superficie verificata

Documentazione ufficiale consultata il **15 settembre 2026**:

- [API Server e Runs API](https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server)
- [Creating Skills](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills)
- [Profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles)

L’adapter usa soltanto:

```text
GET  /v1/capabilities
POST /v1/runs
GET  /v1/runs/{run_id}
POST /v1/runs/{run_id}/stop
```

La creazione invia `input`, `session_id` e `Idempotency-Key`; richiede `run_submission`, `run_status`, `run_stop`. Se la versione installata non espone queste capacità, il test fallisce esplicitamente. Non dipende da un SDK non verificato. Il contratto è coperto da MockTransport e test del bridge, **non da una chiamata LLM live in questa consegna**.

## Setup consigliato: stessa macchina, profilo dedicato

Non riutilizzare un Hermes personale con inbox, SSH o credenziali non pertinenti. Un profilo separa la configurazione, ma per l’isolamento di sicurezza servono anche un utente/container e permessi di rete appropriati.

```bash
# Prima: Vedra installato e scripts/setup.py già eseguito.
hermes profile create vedra
hermes -p vedra setup
python scripts/configure_hermes.py --profile vedra
hermes -p vedra gateway
```

`configure_hermes.py` presume un’installazione nativa locale: il backend raggiunge il gateway a `127.0.0.1:8645`, il terminale del profilo raggiunge Vedra a `127.0.0.1:8000`. Installa solo le due cartelle delle skills. Una seconda installazione richiede `--replace-skills` per evitare sovrascritture involontarie.

Il provider e il modello si configurano in Hermes, non nel browser del cliente. Il codice riusa il modello del profilo. Definisci un budget e un limite operativo nel provider; Vedra impone timeout ma non è un contatore di spesa in euro. Prova inizialmente 5–10 annunci per fonte.

Le variabili del profilo sono:

```dotenv
API_SERVER_ENABLED=true
API_SERVER_HOST=127.0.0.1
API_SERVER_PORT=8645
API_SERVER_KEY=<segreto distinto del profilo>
VEDRA_BASE_URL=http://127.0.0.1:8000
VEDRA_BRIDGE_TOKEN=<stesso valore del backend Vedra>
VEDRA_REQUEST_TIMEOUT=180
```

Nel `.env` di Vedra:

```dotenv
HERMES_BASE_URL=http://127.0.0.1:8645
HERMES_API_KEY=<valore API_SERVER_KEY del profilo>
VEDRA_BRIDGE_TOKEN=<segreto del bridge>
HERMES_TIMEOUT_SECONDS=480
```

Riavvia entrambi quando necessario. Nessuna chiave va incollata nella chat del cliente o committata. Non abilitare CORS del gateway verso la dashboard: le chiamate sono server-to-server.

## Toolset e isolamento

La skill deve poter caricare skills, scrivere un JSON temporaneo e invocare il relativo script Python. Non le servono browser generalista, email, memoria di altre attività o tool amministrativi.

`required_environment_variables` nelle skills dichiara `VEDRA_BASE_URL` e `VEDRA_BRIDGE_TOKEN` per il passthrough al terminale Hermes. `${HERMES_SKILL_DIR}` indica la directory reale della skill quando viene caricata. Gli helper sono Python standard library: nessuna dipendenza da installare nel terminale per usare il bridge.

Le istruzioni anti-prompt-injection non costituiscono una garanzia: un modello con terminale arbitrario può fare più di quanto gli venga chiesto. Usa un ambiente dedicato, senza montare la home personale o il socket Docker; limita l’egress al backend e al provider necessario. Il bridge limita le operazioni di prodotto, ma non è una sandbox del runtime Hermes.

## Protocollo del workflow

1. Vedra raccoglie le fonti in codice e genera task semantici immutabili. Nessun task: conclude senza modello.
2. Avvia il turno Hermes con la skill `vedra-origination`.
3. `collect RUN_ID` legge il risultato già memorizzato e un blocco di task pendenti.
4. La skill `vedra-classification` produce JSON con `summary`, `strategies`, `caveats`, senza numeri modificabili.
5. `submit RUN_ID PROPERTY_ID file.json` valida struttura, citazioni e revisione della fonte. Dopo ogni blocco, `status RUN_ID` restituisce i successivi task (massimo 10). Un estratto troncato è indicato come tale.
6. `finish RUN_ID` è ammesso solo se tutti i task sono presentati. Il worker attende anche lo stato `completed` di Hermes.

La pausa è applicativa; l’annullamento richiede uno stop cooperativo remoto. Alla scadenza del timeout viene richiesto stop e la run fallisce, senza passare silenziosamente a un’altra AI. L’effettivo rilascio di un task remoto dipende dall’executor Hermes; verificare il gateway in caso di blocco.

## Scheduler: una sola fonte di verità

La preview usa la coda e il timer Vedra per la pianificazione del prodotto. La Jobs API Hermes esiste nella documentazione, ma non è necessaria a questa implementazione. Non vengono create automaticamente decine di istanze/profili Hermes.

Per un cron esterno già gestito da Hermes, imposta la ricerca Vedra su **Manuale**, lasciala attiva e usa:

```bash
python3 /percorso/skill/scripts/vedra_bridge.py enqueue AGENT_ID
```

L’endpoint rifiuta ricerche che hanno già una frequenza locale diversa da zero. Una run alla volta per ricerca; il worker della preview esegue una sola run globale per volta.

## Docker e terminali remoti

`127.0.0.1` dentro un container non è la macchina host. La configurazione automatica è deliberatamente per l’installazione nativa. Se il backend o il terminale Hermes è containerizzato, imposta entrambe le direzioni di rete esplicitamente:

- `HERMES_BASE_URL` deve essere raggiungibile dal processo Vedra.
- `VEDRA_BASE_URL` deve essere raggiungibile dall’ambiente che esegue lo script della skill, non soltanto dal gateway.

Preferisci una rete Docker privata tra servizi o una rete privata/VPN con ACL. Il gateway può dover ascoltare su un’interfaccia privata dentro il container, ma non va pubblicato su Internet. Non aggirare il problema esponendo `/bridge` o la chiave Hermes nel frontend. Il reverse proxy pubblico d’esempio blocca `/bridge/*`; Hermes deve usare l’endpoint privato diretto.

La topologia container-Hermes non è stata eseguita in questa consegna. Parti dal collegamento locale, verifica `Impostazioni → Verifica runtime`, esegui una ricerca piccola e ispeziona il log e le citazioni prima della demo AI.

## Troubleshooting

| Segnale | Controllo |
|---|---|
| Runtime non configurato | `.env` Vedra: chiave Hermes e bridge valorizzati; riavvio effettuato |
| 401 Hermes | Chiave del profilo corretto, non quella di un altro profilo |
| Capacità mancanti | Versione/gateway che esponga la Runs API documentata |
| Bridge non raggiungibile | Rete vista dal terminale, `VEDRA_BASE_URL`, porta, variabili passate alla skill |
| 422 sull’analisi | Campi extra, strategia non ammessa, citazione assente o duplicata |
| 409 contenuto cambiato | Nuova run con evidenze aggiornate; non ignorare il controllo |
| `finish` rifiutato | Esistono ancora task pendenti; chiedere il prossimo blocco con `status` |
| Hermes termina senza protocollo | Skill non caricata/seguita o tool non disponibile; la run è correttamente segnata failed |
| Nessuna chiamata AI | Non esiste delta semantico: comportamento previsto, non un malfunzionamento |

Le metriche `usage` vengono registrate se restituite da Hermes. Non vengono convertite in costi monetari inventati.
