# Hermes opzionale: profilo verticale, non un fork

Vedra funziona con regole oppure con un provider Chat Completions senza Hermes.
Questa integrazione è per chi preferisce il suo runtime e il suo provider configurato.
Con `online_discovery` Hermes avvia la ricerca nelle fonti HTML configurate, sceglie
gli URL e ne richiede la lettura. Vedra verifica domini, robots, estrazione e persistenza.
Senza questa opzione, Vedra raccoglie prima e Hermes riceve i task semantici.

## Installazione nativa dedicata

Hermes va installato separatamente dal progetto ufficiale. Non riusare il profilo
personale, la home con credenziali, email/SSH o un terminale generalista del cliente.
Dopo il setup Vedra:

```bash
python -m pip install -r requirements-hermes.txt
hermes profile create vedra
hermes -p vedra setup
python scripts/configure_hermes.py --profile vedra
hermes -p vedra gateway
```

Riavvia Vedra dopo il configuratore. Il comando conserva la configurazione del
provider, salva una copia del `config.yaml` preesistente e configura un profilo
**ristretto**. Un'installazione delle skills già presente richiede `--replace-skills`.
Leggi `python scripts/configure_hermes.py --help` per percorsi/porte alternativi.
Le chiavi generate non vengono stampate.

Il profilo espone il solo toolset `vedra` su `api_server` e `cli`:

```yaml
platform_toolsets:
  api_server: [vedra]
  cli: [vedra]
mcp_servers:
  vedra:
    command: /percorso/.venv/bin/python
    args: [/percorso/vedra/hermes/mcp/server.py]
    tools:
      include: [search_listings, browse_source, acquire_listing, complete_collection, get_tasks, submit_analysis, finish_run]
      resources: false
      prompts: false
```

Lo script scrive i percorsi reali e l'ambiente del processo MCP. Il server MCP non
ha una chiave generale del workspace. **Una skill testuale non è una sandbox**:
prima della run Vedra legge l'elenco effettivo `/v1/toolsets` e richiede esattamente
i sette strumenti `mcp__vedra__*` elencati sopra per la ricerca online. La modalità
solo analisi accetta anche il precedente profilo di tre strumenti. Strumenti
aggiuntivi o mancanti fermano l'avvio. Questo non sostituisce isolamento OS/rete
né una revisione della versione concreta di Hermes.

## Superficie e protocollo

API documentate: `GET /v1/capabilities`, `GET /v1/toolsets`, `POST /v1/runs`,
`GET /v1/runs/{id}`, `POST /v1/runs/{id}/stop`.
La richiesta usa `input`, `session_id`, `Idempotency-Key`.

1. Vedra acquisisce, valida e prepara task con hash della revisione.
2. Zero task: nessuna chiamata Hermes. Altrimenti genera una capability a tempo,
   limitata alla run, conservandone soltanto l'hash nel database.
3. Hermes chiama `get_tasks`, interpreta fino a 10 record per blocco e chiama
   `submit_analysis` per ciascuno. Tutto il testo del listing è non fidato.
4. Il backend valida struttura, citazioni e hash; modifica solo l'analisi.
5. Quando non restano task, `finish_run`; Vedra attende anche il completamento
   remoto. La capability viene revocata alla chiusura o al riavvio.

Niente terminale, file, browser generico, memoria generalista o tool per accodare altre
ricerche. Le skills descrivono questo workflow e sono versionate nel repository.
Gli helper `hermes/scripts/vedra_bridge.py` e le copie legacy nelle skills sono
mantenuti per compatibilità amministrativa, **non sono gli strumenti del modello**.
L'eventuale token generale `VEDRA_BRIDGE_TOKEN` non deve essere dato a Hermes.

Il profilo API è privato: `API_SERVER_HOST=127.0.0.1`, porta 8645 predefinita,
chiave distinta. La dashboard non vede mai le chiavi. In Docker la loopback non
raggiunge l'host; predisporre rete privata e indirizzi coerenti in entrambe le
connessioni Vedra→Hermes e MCP→Vedra, senza esporre `/bridge` pubblicamente.

## Pianificazione

Vedra rimane l'unico scheduler del prodotto. Non creare anche un cron Hermes per
la stessa ricerca. Il worker esegue una run globale alla volta. La pausa impedisce
future esecuzioni programmate; lo stop della run già iniziata è un'azione distinta.
Timeout e annullamento inviano lo stop al gateway; verificare sul runtime remoto
che le attività siano realmente terminate.

## Verifica concreta

`Impostazioni → Verifica runtime` controlla presenza del gateway/capacità, ma non è
un test LLM completo. Crea una ricerca piccola, seleziona Hermes e controlla task,
citazioni e completamento. I test inclusi simulano il protocollo e provano il
bridge, non una sessione reale sul gateway dell'utente.

Fonti ufficiali consultate per l'adapter (16 settembre 2026):
- https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server
- https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp
- https://hermes-agent.nousresearch.com/docs/user-guide/profiles

Il runtime esterno può cambiare: bloccare/versionare l'installazione validata dal
cliente, non assumere che qualunque futuro aggiornamento sia compatibile.

## Runtime verificato su Oracle (19 settembre 2026)

La versione dedicata 0.20.5, commit
`261a4efb90d7dbe4e71786861858f721b4ab730c`, restituisce `/v1/toolsets`
come `{object: "list", platform: "api_server", data: [...]}` e registra i nomi
`mcp__vedra__get_tasks`, `mcp__vedra__submit_analysis`, `mcp__vedra__finish_run`.
Il client accetta questo contratto e quello precedente, ma richiede sempre
esattamente uno degli insiemi di strumenti documentati sopra: sette per il browser; i precedenti profili da tre o sei restano compatibili
con le modalità senza navigazione.

In questa versione l'endpoint enumera solo il menu interattivo e omette gli MCP.
La patch `deploy/hermes-api-toolsets.patch`, applicata esclusivamente alla copia
Hermes dedicata, aggiunge discovery e risoluzione dal registro effettivo. Non
inventa strumenti e non modifica il profilo personale. Applicare con `git apply`
solo dopo aver verificato commit e contesto; riesaminare la patch agli aggiornamenti.
Il servizio necessita anche dei pacchetti opzionali `aiohttp` e `mcp`.

## Ricerca online avviata da Hermes

Attivare `criteria.online_discovery` con runtime `hermes`. Il profilo necessita
almeno di 24 turni per una piccola ricerca con acquisizione e analisi. La sequenza è
`search_listings` → `acquire_listing` per gli URL scelti → `complete_collection` →
`get_tasks` / `submit_analysis` → `finish_run`. Il backend non pre-carica annunci.
Ogni URL deve essere presente nei risultati di questa run; i valori sono estratti
nuovamente dalla pagina, senza accettare prezzo o descrizione inventati dal modello.
Gli eventi `hermes_discovery` e `hermes_acquire` documentano le operazioni effettive.

La ricerca copre le fonti configurate, non tutto il mercato. Gli annunci già presenti
sono aggiornati e deduplicati a ogni lettura. La frequenza usa lo scheduler Vedra.
Il preset `examples/scm-milano.source.json` non concede diritti sulla fonte: occorre
verificare e confermare il contesto d'uso prima di abilitarlo. `retain_raw_html=false`
conserva il record estratto invece dell'HTML completo e omette le immagini.

Il 22 settembre 2026 due run effettive hanno completato rispettivamente quattro
e cinque acquisizioni senza errori. Sei record hanno cambiato stato dopo il
controllo delle immagini. È una verifica della fonte configurata, non dei portali
generalisti. La navigazione interattiva resta distinta: vedi `PORTAL_ACCESS.md`.

## Spostare il runtime

Il collegamento usa `HERMES_BASE_URL`, `HERMES_API_KEY` e l'origine Vedra nel
processo MCP. Nessun indirizzo della VPS o account personale è parte del contratto.
Per un'altra installazione, creare un profilo dedicato, rieseguire il configuratore
e verificare capacità, strumenti, avvio, stop e una piccola run completa. Non
copiare database di sessione, cookie o credenziali del profilo personale.

Un aggiornamento o un runtime gestito internamente deve superare gli stessi test
di contratto. Non serve un fork per cambiare host o provider del modello.

## Cataloghi nel browser

`config.browser_navigation=true` affida la navigazione del catalogo a Hermes.
`search_listings` restituisce le fonti da aprire; `browse_source(source_id, ref="")`
apre la ricerca configurata in Chromium. Il modello legge testo e candidati e
segue `next_ref` per le pagine successive. Non può fornire URL, script o form.
I riferimenti e il budget pagine sono persistiti per run; la raccolta richiede
che ogni fonte browser sia stata controllata. `acquire_listing` riapre il dettaglio
nel browser e salva fatti estratti dal codice, disponibilità e provenienza.

Attivare `BROWSER_ENABLED`, installare l'extra Playwright e impostare eventualmente
`BROWSER_EXECUTABLE_PATH` al Chromium dedicato. Rieseguire il configuratore del
profilo Hermes per esporre `browse_source`; verificare sette tool e una run reale.
Il browser usa connessioni native con DNS fissato all'indirizzo pubblico verificato,
dominio esatto, robots, sola lettura e sandbox attiva. WebSocket, WebRTC,
WebTransport, service worker, download e richieste mutative sono esclusi.
Ogni pagina ha un contesto isolato: login, cookie persistenti, moduli e filtri
interattivi non sono ancora supportati. Il connettore JavaScript precedente resta
disponibile separatamente tramite `render_js`.

Il test `test_native_chromium_catalog_to_persisted_listing`, abilitato con
`BROWSER_TEST_EXECUTABLE`, usa Chromium reale e un server locale temporaneo con
fixture: verifica un link creato da JavaScript e il salvataggio del dettaglio.
Non dimostra accesso ai portali esterni o una chiamata al modello.

La navigazione nativa controlla anche `Location` prima di seguire ogni redirect,
tramite l'intercettazione delle risposte Chromium. Il solo `route.continue_()`
non basta: Playwright intercetta soltanto il primo URL della catena
([documentazione](https://playwright.dev/python/docs/api/class-page#page-route)).
Le finestre secondarie vengono bloccate e i contesti chiusi anche in caso di errore.
Le risorse di domini diversi dalla fonte restano escluse; i portali che le richiedono
necessitano di un adapter verificato. Non sono mascherati come cataloghi supportati.
