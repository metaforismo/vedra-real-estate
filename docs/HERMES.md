# Hermes opzionale: profilo verticale, non un fork

Vedra funziona con regole oppure con un provider Chat Completions senza Hermes.
Questa integrazione è per chi preferisce il suo runtime e il suo provider configurato.
La raccolta resta locale e deterministica: Hermes vede soltanto task semantici.

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

Il profilo espone il solo toolset `mcp-vedra` su `api_server` e `cli`:

```yaml
platform_toolsets:
  api_server: [mcp-vedra]
  cli: [mcp-vedra]
mcp_servers:
  vedra:
    command: /percorso/.venv/bin/python
    args: [/percorso/vedra/hermes/mcp/server.py]
    tools:
      include: [get_tasks, submit_analysis, finish_run]
      resources: false
      prompts: false
```

Lo script scrive i percorsi reali e l'ambiente del processo MCP. Il server MCP non
ha una chiave generale del workspace. **Una skill testuale non è una sandbox**:
prima della run Vedra legge l'elenco effettivo `/v1/toolsets` e richiede esattamente
`mcp_vedra_get_tasks`, `mcp_vedra_submit_analysis`, `mcp_vedra_finish_run`. Strumenti
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

Niente terminale, file, browser, memoria generalista o tool per accodare altre
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
