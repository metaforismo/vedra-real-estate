# Acquisizione, importazioni e qualità

## Cataloghi disponibili

`demo`: HTML sintetici generati localmente; non effettua HTTP.

`html`: connettore generico con URL della ricerca, paginazione, JSON-LD e selettori CSS. Richiede dominio esatto nella allowlist del server e dichiarazione documentata del permesso. Il browser Playwright è una modalità opzionale dello stesso connettore.

`import`: CSV normalizzato o singolo HTML già ottenuto con titolo di utilizzo. Nessun download viene effettuato durante l’importazione HTML.

Non sono presenti adapter provati su Idealista, Immobiliare.it, Casa.it, PVP o Astalegale. Non si pretende di bypassare i loro controlli. `fixtures/source.example.json` è un tracciato, non un dominio funzionante.

## Come configurare una fonte HTML

Il pattern URL è una sottostringa letterale del percorso, non una regex. Esempio: `/immobili/`. I link fuori dal dominio esatto vengono esclusi. `{city}` nella ricerca viene sostituito con il comune in minuscolo, spazi trasformati in trattini e caratteri percent-encoded.

I selettori dei campi leggono `content` se presente (utile per i meta tag), altrimenti il testo del nodo. Esempio per un sito autorizzato che esponga questi elementi:

```json
{
  "price": ".price",
  "surface": ".surface",
  "currency": "meta[itemprop='priceCurrency']",
  "city": ".city",
  "zone": ".zone",
  "property_type": ".asset-type",
  "condition": ".condition",
  "area_basis": ".area-basis",
  "transaction_type": ".transaction"
}
```

Le classi dell’esempio non sono garantite sui portali. Calibra i selettori sulla fonte concreta e verifica i valori, non soltanto lo status HTTP. I campi JSON-LD riconosciuti includono prezzo, valuta, `floorSize`, località, indirizzo, locali, bagni, coordinate, immagini e `businessFunction`. Metadati normalizzati espliciti in `additionalProperty` possono fornire micro-zona, stato, tipologia, base di superficie e operazione.

Non viene letto genericamente qualunque JSON proprietario incorporato nel sito. Non c’è OCR di screenshot o PDF. Il browser rende HTML, non conferisce al modello accesso generalista al web.

## Politica di rete incorporata

- Esatta allowlist del dominio, schema HTTP(S), nessuna credenziale nella richiesta, nessun proxy d’ambiente.
- DNS verificato contro IP privati/riservati; connessione all’IP verificato con hostname e TLS SNI originari.
- Ogni redirect viene rivalidato e non può uscire dal dominio o raggiungere un percorso disabilitato in robots.
- `robots.txt` verificato; errori di verifica fermano la fonte, 404 viene trattato come assenza del file, non come una licenza commerciale.
- Minimo 2 secondi tra richieste della stessa istanza del connettore, aumentato dal crawl-delay; 20 secondi di timeout per richiesta.
- Massimo 5 pagine di ricerca, 100 annunci per fonte/run, 200 richieste HTTP per fonte/run incluse le risorse browser; HTML massimo 3 MB.
- Stop su 401/403/429, challenge riconosciute o risposte non valide. Niente CAPTCHA bypass, stealth o proxy rotation.

La conferma dei diritti nella UI è una dichiarazione dell’operatore: non è un’autorizzazione rilasciata dal sito. I limiti tecnici non sostituiscono la verifica del diritto di accesso, trattamento o riuso.

### Browser opzionale

```bash
python -m pip install playwright==1.57.0
python -m playwright install chromium
```

Imposta `BROWSER_ENABLED=true`, riavvia e seleziona “Rendering browser” nella fonte. In Linux possono servire le dipendenze di sistema: `python -m playwright install --with-deps chromium` su un ambiente controllato.

Le richieste vengono inoltrate dal browser attraverso il fetcher verificato. Service worker, websocket, richieste non GET, media, download e traffico cross-origin sono bloccati. Cookie/login persistenti e sessioni di portali non sono implementati. Questo comportamento protegge il perimetro ma può impedire il funzionamento di siti che usano CDN o API su altri domini. Non rimuovere il controllo SSRF per aggirare un’incompatibilità; creare un adapter controllato.

## Sitemap e aggiornamento dei dettagli

`discovery_mode=sitemap` legge una sitemap XML di URL, con limite annunci.
Gli indici di sitemap non sono percorsi ricorsivamente. DTD/entità XML sono
rifiutati. Ogni pagina scoperta passa comunque dagli stessi controlli di rete.
`detail_refresh_hours` (1–720, default24) evita di rileggere pagine invariate a ogni
heartbeat. Il prezzo può cambiare durante la finestra: il dato rimane osservato
alla data del suo ultimo fetch. Non dichiariamo monitoraggio real-time delle modifiche.

Errori fonte producono cooldown persistente, pausa e contatori. `Verifica fonte`
serve a riprovare esplicitamente dopo aver corretto la configurazione. Un successo
ripristina lo stato. Il contatore delle richieste pagina non è un contatore HTTP
completo con robots/asset browser. I record assenti da una scansione parziale non
sono eliminati né classificati come venduti.

## CSV immobili

UTF-8, separatore virgola, punto e virgola o tab. Esempio completo in `fixtures/imports/properties-demo.csv`.

| Campo | Significato |
|---|---|
| `listing_key` | Identità stabile della fonte. Consigliata, specialmente se non c’è una URL stabile. |
| `url` | URL di provenienza; se assente viene creata un’identità di import dal contenuto. Con un’identità derivata da tutto il contenuto, un cambio prezzo può creare un nuovo record: fornire una chiave stabile. |
| `title` | Obbligatorio. |
| `price`, `surface` | Numeri. Prezzo assente resta nullo; la superficie è espressa in m² e deve essere almeno 0,1. |
| `currency` | Codice esplicito, ad esempio EUR. Assente = XXX/sconosciuta. Nessuna conversione valuta. |
| `transaction_type` | `sale`, `rent`, `unknown`. Assente = unknown. |
| `city`, `zone`, `address` | Comune e micro-zona; non vengono geocodificati automaticamente. |
| `property_type` | `residential`, `office`, `commercial`, `logistics`, `land`, `hospitality`, `unknown`. |
| `condition` | `new`, `good`, `to_renovate`, `shell`, `unknown`. |
| `area_basis` | `commercial`, `net`, `gross`, `unknown`. |
| `description` | Testo, massimo 30.000 caratteri. |
| `rooms`, `bathrooms`, `latitude`, `longitude`, `is_auction` | Opzionali; coordinate non equivalgono a precisione verificata. |

Usa numeri senza separatori delle migliaia nei CSV generati da software. Il parser dei testi adotta virgola decimale italiana e punto come migliaia quando il raggruppamento è compatibile. `620,000` significa 620, non 620 mila. Formati ambigui vanno normalizzati a monte.

Campi sconosciuti vengono ignorati per il CSV immobili; `score`, `evidence`, `images` e il flag demo non sono accettati come override dal file. La natura demo/reale deriva dalla selezione esplicita della finestra di import. Massimo 2.000 righe e 4 MB per importazione. Le righe vengono validate prima di iniziare gli inserimenti; errori di storage durante la scrittura possono comunque lasciare importazioni parziali, da controllare e ripetere con chiavi stabili.

## CSV benchmark

Campi obbligatori:

```text
city,zone,property_type,condition,area_basis,currency,transaction_type,
min_sqm,max_sqm,period,source_label,source_url
```

Periodo `YYYY-S1` o `YYYY-S2`. Fonte e periodo devono essere quelli reali, non la data di download scelta arbitrariamente. Gli esempi sono sintetici e riportano “NON OMI”. Reimportare la stessa serie e periodo sostituisce il record. Periodi futuri o riferimenti oltre 18 mesi non vengono usati.

I file originali di OMI o di altri fornitori richiedono una conversione esplicita in questo tracciato. In particolare normalizzazione dei comuni, codici di micro-zona, tipologie, stato e superficie non va sostituita con guess dell’LLM. Se non coincide la base del confronto, il benchmark non viene abbinato. Il valore confrontato è il punto medio del range, non una media di transati.

## Cosa misura la qualità

Completezza = presenza di dieci campi: prezzo, superficie, titolo, descrizione, comune, zona, indirizzo, tipo, stato, base della superficie. I campi sconosciuti non sono presenti. La misura non include accuratezza, precisione geografica, freschezza, copertura dell’intero mercato o attendibilità dell’inserzionista.

La dashboard mostra il campione effettivamente acquisito; non afferma di aver scoperto tutti gli annunci di un portale. L’hash del testo identifica una versione, non ne certifica la veridicità. L’indirizzo serve a segnalare duplicati candidati, non a unire automaticamente unità diverse.

## Export

CSV: UTF-8 con BOM e separatore `;`, testi pericolosi per le formule neutralizzati, valuta esplicita.

XLSX: tabella con filtri, formule di prezzo/m² e delta, cache numeriche già valorizzate per i lettori che non ricalcolano, ricalcolo automatico in Excel, commenti con fonte benchmark, foglio “Metodo e limiti”. Il CSV contiene valori, non formule. Gli export non costituiscono modelli di rendimento.

DOCX: scheda con dati, strategie e citazioni, provenienza, metodo e avvertenze. Nessuna perizia o margine inventato. Prezzi e valute sconosciute restano distinti.

## Dati di prova

`python scripts/generate_examples.py` rigenera soltanto fixture sintetiche, anche aggiornando il periodo demo all’anno corrente. Non effettua rete e non altera il database. Importa questi esempi esclusivamente come **Dimostrativo / sintetico**.
