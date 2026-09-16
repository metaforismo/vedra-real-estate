# Classificazione AI configurabile

Il runtime `llm` è un client server-side per `/chat/completions`. Non implementa
un assistente con terminale arbitrario. Il timer, la rete delle fonti, le chiavi,
il database e le formule restano in codice Vedra. L'AI interpreta soltanto
annunci selezionati dalle regole. Ogni risultato conserva engine/model e citazioni.

## Contratto del provider

Richiesta: `model`, `messages`, `max_completion_tokens`, `stream:false`.
`AI_REASONING_EFFORT`, quando valorizzato, viene inviato come `reasoning_effort`.
`AI_RESPONSE_FORMAT` supporta `json_object` (default), `json_schema` oppure `none`.
Con `none` la validazione JSON locale rimane obbligatoria. Endpoint senza redirect,
HTTPS per host remoti; HTTP è ammesso solo per loopback e test locali.

Un provider compatibile deve restituire `choices[0].message.content` con un JSON:

```json
{
  "summary": "Sintesi in italiano, non una perizia",
  "strategies": [
    {"strategy": "value_add", "evidence": "da ristrutturare"}
  ],
  "caveats": ["Informazioni da verificare sulla documentazione dell'immobile"]
}
```

Strategie: `value_add`, `core_plus`, `development`, `conversion`. La citazione deve
essere nel testo fornito e non supportare una negazione della strategia. Campi extra,
output incompleto o tool call vengono rifiutati. Un JSON formalmente valido non
prova la correttezza semantica della sintesi: controllare risultati e falsi positivi
su un campione umano prima di usarli nelle decisioni.

L'adapter invia titolo, descrizione (task limitati a 6.000 caratteri), tipo, stato e
flag sintetico. Non invia note private, altri immobili, chiavi di servizi o il
contenuto del database. Il testo è trattato come input non fidato e non può
attivare browsing o comandi. Scelta provider e trattamento dei dati vanno valutati
separatamente per ogni cliente.

## Costi e limiti

Zero task semantici significa zero richieste AI. Record invariati già analizzati
dallo stesso modello non vengono rianalizzati. Cambiando modello o descrizione,
il record torna candidabile; una modifica del solo prompt non invalida da sola
la cache, quindi va validata in una run/dataset di prova separata.

Massimo `AI_MAX_ANALYSES_PER_RUN`, `RUN_TIMEOUT_SECONDS`, timeout per richiesta e
`AI_MAX_OUTPUT_TOKENS`. Una run che raggiunge il limite di analisi diventa parziale;
i dati restano e le analisi residue vengono riprese da una successiva raccolta.
Al massimo un retry per 429/5xx con attesa breve; nessun modello alternativo
silenzioso. Un `Retry-After` lungo restituisce il controllo al timer.

`usage` viene registrato soltanto per risposte accettate. Le stime in euro richiedono
entrambe le tariffe configurate e i token dichiarati dal provider. Non sono un
contatore fatturabile completo: retry, timeout e output rifiutati possono essere
addebitati senza comparire nel totale. Impostare limiti di spesa anche presso il
provider. Nessuna telemetria di token falsa o stima di latenza precompilata.

## Regolo: solo test locale

L'esempio `examples/regolo.local.env.example` usa il modello esatto indicato dal
committente: `qwen3.8-27b`. È una configurazione facoltativa, non una verifica del
catalogo del provider o dei prezzi. Le tariffe riportate sono quelle fornite
dall'utente e vanno confermate nel suo account.

Copia i valori nel `.env` privato senza aggiungere una seconda occorrenza della
stessa variabile, inserisci una nuova chiave e riavvia. Le variabili già esportate
nella shell prevalgono sul file. Non committare chiavi; ruotare quelle già condivise.

```bash
python scripts/check_ai.py
python scripts/check_ai.py --live --accept-cost
```

Il secondo comando può addebitare una classificazione sintetica e un eventuale
retry. Il superamento verifica solo il contratto semantico: non verifica portali,
coverage, stato in esecuzione per ore o qualità su immobili reali.

## Hermes alternativo

Vedi [HERMES](HERMES.md). Il database/scoring/collector non dipendono da Hermes,
quindi il prodotto non richiede un suo fork. La separazione consente di cambiare
runtime senza migrare gli immobili o la dashboard.
