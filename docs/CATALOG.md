# Archivio completo e revisione — 0.4

## Query e numeri

`GET /api/catalog` restituisce `items`, `total`, `page`, `pages`, `page_size`,
`has_next`, `computed_at`, `scope=full-archive`. Taglio di pagina tra 10 e 100 record
(default 50); UI 25/50/100. Una pagina oltre l’ultima viene riportata all’ultima
pagina esistente. Archivio vuoto: pagina 1 di 1, totale 0.

Filtri validati: `q`, `city`, `type`, `strategy`, `source_id`, `currency`, `status`,
`agent_id`, `qualified`, `starred`, `min_price`, `max_price`, `min_surface`,
`max_surface`, `focus`. `sort`: score, price, latest, newest, quality, due.
Valori vincolati e placeholder SQL; %, _ e ! nella ricerca sono letterali.
Un intervallo prezzo richiede una valuta; valori mancanti sono esclusi dai range.
`qualified=true` insieme ad `agent_id` richiede che sia **quell’agente** ad aver
qualificato l’annuncio, non un altro agente.

L’ordine ha un discriminante ID stabile. La paginazione usa offset, non un cursore
snapshot: nuove acquisizioni o aggiornamenti durante la navigazione possono spostare
le righe. Le decisioni sono basate su ID/versioni, mai sulla posizione nella pagina.
Il numero è di **annunci**, non di asset fisici distinti. I comparabili mantengono il
proprio trattamento dei duplicati confermati.

`GET /api/catalog/facets` dà comuni (massimo 1.000, `cities_truncated` se ecceduti),
valute osservate e totale reale. I record sintetici legacy non sono esposti.

Le viste rapide sono filtri operativi, non inferenze di mercato:
- new: acquisito nei 7 giorni precedenti, non pubblicato necessariamente in quel periodo;
- stale: ultima rilevazione oltre 7 giorni, non venduto o rimosso;
- unbenchmarked: nessun benchmark collegato;
- overdue: scadenza precedente alla data UTC odierna e stato non chiuso;
- unassigned: nessun responsabile e stato non chiuso.

## Revisione multipla

`POST /api/catalog/selection` legge la selezione attuale (1–100 ID distinti).
`POST /api/catalog/review` accetta `items: [{id,version}]`, `stage` e `note`.
Un solo record mancante o con versione diversa produce 409 e rollback completo.
Responsabile, scadenza e checklist non cambiano. La nota facoltativa viene aggiunta
ad ogni annuncio; per `discarded` servono almeno 5 caratteri di motivazione.
Stesso stato senza nota è un no-op e non incrementa la versione.

Il ruolo viewer non può modificare. CSRF e permessi sono gli stessi delle altre API.
Audit e note condividono la transazione dell’aggiornamento. Il frontend rilegge la
selezione prima della conferma; il controllo versione protegge l’intervallo successivo.

## Export

`POST /api/catalog/export`: `format` csv/xlsx, `filters` come sopra, massimo 2.000
righe per esportazione. Oltre il limite: 422 con istruzioni, **nessun troncamento**.
Header `X-Vedra-Export-Count` indica le righe. La selezione usa l’endpoint esistente
`POST /api/export` con lookup completo per ID, non il campione in memoria.
L’export GET legacy applica anch’esso il limite in modo esplicito: per una selezione
ampia usare POST. L’export non è un archivio immutabile: rappresenta il database al
momento della richiesta, non una precedente sessione di lettura.

## Cronologia delle evidenze

`GET /api/properties/{id}/history?limit=30&before={observation_id}`.
Massimo 50; cursore appartenente allo stesso immobile. L’elemento extra letto è
usato come precedente per confrontare l’ultima riga della pagina. Campi tracciati:
titolo, prezzo, superficie, valuta, operazione, base superficie, categoria, stato,
comune, zona, indirizzo, locali, bagni, coordinate, asta e descrizione.

Variazioni derivano da coppie di `observation_values` salvate nell’acquisizione.
Le analisi AI e le correzioni alla riga corrente non cambiano questo storico.
Nessuna osservazione prima della migrazione è arricchita retroattivamente.
La UI distingue prima evidenza, campi non conservati e confronto effettivo. Prezzi
in valute diverse non vengono trasformati in sconti impliciti.

## Diagnostica e responsabilità

`GET /api/agents/{id}/preflight` è solo locale: nessun HTTP esterno, modello o spesa.
Controlla runtime configurato, fonti, allowlist, permesso dichiarato, browser, cooldown,
import presenti, worker e scheduler. Una fonte import non acquisisce nuovi annunci.
I risultati di Test sono invalidati quando viene riconfigurata una fonte; il cooldown
non viene cancellato. La diagnostica non testa realmente la raggiungibilità del sito.

La run manuale senza fonti/runtime configurati viene rifiutata con 409. Un worker
spento non impedisce di accodare: la UI avvisa che servirà avviarlo. La programmazione
rimane responsabilità del worker e i controlli a runtime continuano ad essere applicati.
