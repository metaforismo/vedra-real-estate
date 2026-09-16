# Fonti, provenienza e insight

## Fonti operative

`html`: ricerca HTML/JSON-LD/CSS, dati JSON incorporati configurabili, sitemap XML
e rendering browser opzionale. `import`: CSV normalizzato o HTML acquisito
legittimamente. Non esiste un catalogo dimostrativo disponibile nell'app. Le
fixture sotto `backend/tests/` non vengono esposte dal server né copiate nelle
immagini Docker del prodotto.

Non sono inclusi connettori specifici collaudati sui principali portali. L'operatore
deve verificare accesso autorizzato, qualità e condizioni di riuso di ogni fonte.
Non si aggirano CAPTCHA, login, anti-bot o divieti della fonte.

## Configurazione dalla dashboard

Imposta prima `LIVE_ALLOWED_DOMAINS` con host esatti nel `.env` del server. Crea una
fonte con dominio, URL ricerca, selettori e permesso documentato. `{city}` nell'URL
usa il comune dell'agente (minuscolo, spazi→trattini, percent-encoding). Il test
manuale usa **Comune di verifica** (`probe_city`), non una città inventata.

Il pattern dei link è una sottostringa del percorso, non una regex. La query deve
restituire davvero annunci della zona/tipo desiderati: scegliere Milano nella UI
non corregge un URL che restituisce tutta Italia. Mantieni limiti di pagine e
intervalli compatibili con l'autorizzazione del sito.

**Verifica fonte** visita una pagina e al massimo un dettaglio, senza importare
annunci. Mostra campi mancanti, completezza e ultima verifica. Un HTTP 200 senza
dati utilizzabili non è un successo. Un blocco produce backoff persistente: il
pulsante di verifica non lo aggira. Il test non garantisce copertura né continuità.

Le importazioni accettano intestazioni descritte nei modelli CSV scaricabili dalla
UI; i modelli contengono solo intestazioni, nessun immobile di esempio. Campi non
conosciuti rimangono null/unknown. I parametri di contesto dichiarati dall'operatore
restano distinti dai campi estratti con evidenza.

## Confronti affidabili

Valuta, transazione (vendita/locazione), tipologia, stato e base della superficie
devono essere compatibili. Non confrontare una base d'asta con un ask ordinario, un
canone mensile con un prezzo di vendita o una superficie calpestabile con quella
commerciale. I benchmark vanno importati con fonte, periodo e intervallo; nessuna
quotazione OMI viene scaricata o inventata automaticamente.

Un ribasso è osservato tra revisioni di uno stesso annuncio con contesto omogeneo,
non dedotto da un campo corrente. Le osservazioni antecedenti alla v3 prive di
contesto non diventano ribassi verificati. Un annuncio vecchio/non visto non viene
marcato come venduto. «Giorni osservati» non equivale a Days on Market completo.

I segmenti di mercato usano solo l'archivio della piattaforma: città, zona, tipo,
stato, fascia di superficie, valuta e transazione compatibili. Servono almeno
cinque asset distinti per mostrare mediana/quartili. Le duplicazioni confermate
contano una volta. Fonti, numerosità e troncamento del campione sono espliciti:
non è un indice dell'intero mercato né un prezzo transato o una perizia.

## Immagini

Aggiungi separatamente gli host autorizzati a `IMAGE_ALLOWED_DOMAINS`. Il proxy
richiede login e accetta solo la prima immagine registrata nell'annuncio, non URL
arbitrari. Valida firma JPEG/PNG/WebP, dimensione, DNS e limiti; vieta SVG/HTML.
Cache privata limitata e placeholder sobrio in caso di assenza/blocco. Non sono
incluse fotografie immobiliari di riempimento.

## Conservazione

Snapshot ed evidenze servono alla verifica, non autorizzano la redistribuzione.
Configura durata di conservazione, backup, accessi e procedure privacy con il
cliente. La pulizia legacy è esplicita, con backup e scritture ferme; non cancella
automaticamente file storici o backup. Vedi `UPGRADE.md`.
