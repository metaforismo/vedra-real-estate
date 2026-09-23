# Verifiche live

Ultimo aggiornamento: 23 settembre 2026. Dati operativi e credenziali restano fuori dal repository.

## Stato attuale

Hermes ha completato una ricerca browser su due cataloghi pubblici. La prima
acquisizione ha aggiunto tre immobili reali nel budget impostato. Il ricontrollo
automatico, dopo la correzione dell’estrattore, ha recuperato comune e zona dei
record incompleti: tre risultano ora nei criteri, con immagini e provenienza.
Nessuna correzione manuale dei record e nessun dato QA importato.

Ricerca e verifica dei dettagli sono configurate ogni sei ore; i campi essenziali
mancanti anticipano il ricontrollo entro il limite della fonte. Valori di mercato e rendimenti
non sono stimati quando mancano dati confrontabili. I portali generalisti non
sono ancora coperti. Le verifiche precedenti sono conservate sotto.


## Ricerca periodica e disponibilità

La ricerca è configurata ogni 6 ore. Per verificare il percorso automatico è stata
anticipata una singola scadenza: il worker ha avviato una run con trigger `schedule`,
senza usare il pulsante Esegui. Il ciclo è terminato `completed` e ha salvato la
prossima scadenza sei ore dopo la conclusione.

| Controllo | Risultato |
| --- | --- |
| Link nella fonte configurata | 20 |
| Annunci ricontrollati | 3 |
| Nuovi annunci acquisiti | 1 |
| Annunci aggiornati | 3 |
| Annunci compatibili dopo la verifica | 1 |
| Errori | 0 |

Due annunci riportavano “venduto” nelle immagini. L'OCR sul server ha rilevato
le diciture; entrambi hanno priorità zero e sono esclusi dalla vista predefinita
nonché dai criteri degli agenti. Il record segnalato è rimasto consultabile con
filtro Venduti, immagine originale e provenienza. Per la scritta inclinata la
confidenza OCR osservata è 91,8: non è una probabilità di vendita.

Il nuovo annuncio, distinto dai precedenti, dimostra che la stessa esecuzione
combina aggiornamento e nuova acquisizione. La fonte copre soltanto il catalogo
configurato; non rappresenta tutto il mercato. Il collaudo non attesta variazioni
reali di prezzo né una riapertura di un annuncio precedentemente chiuso.

La priorità operativa espone i suoi fattori e resta distinta dal confronto di
prezzo. I confronti omogenei e le statistiche di mercato escludono annunci chiusi
o con verifica fallita. L'assenza di disponibilità confermata resta visibile.

## Riferimenti nazionali e immagini

- Catalogo OMI: 103 voci provinciali e 7.890 codici comunali unici della fonte.
  Quotazioni consultate per Milano, Bari e Cosenza, periodo 2025/2. Non sono
  suddivisioni amministrative certificate come attuali né copertura degli annunci.
- Assegnazione della zona OMI tramite coordinate pubblicate e poligoni ufficiali.
  La precisione dell'indirizzo rimane da verificare.
- Sei immagini caricate via proxy autenticato e visualizzate nella scheda.
- Scenari OMI condizionati con stato, tipologia e base della superficie espliciti.
  Non vengono presentati come perizie o intervalli di confidenza.

## Collaudo

- 344 test Python passati prima delle ultime correzioni; successivi controlli mirati
  coprono cicli senza novità, refresh obbligatori, disponibilità, migrazioni e comparabili.
- Quattro integrazioni PostgreSQL e sei test disponibilità passati su server in un
  database temporaneo distinto da quello operativo.
- 15 moduli JavaScript, 8 controlli mappa, 7 test catalogo, 7 controlli dei processi
  e 18 scenari UI locali passati. Nessun errore JavaScript nel collaudo UI.
- I 18 scenari includono login, filtri, paginazione, revisioni, scenari, fonti,
  importazione, esecuzione/pause degli agenti, tema scuro e mobile a 393 px.
- Disponibilità e priorità verificate sul sito live e mediante API autenticata.
- Il backup del database precede la migrazione additiva della disponibilità.

Questi controlli verificano i percorsi descritti, non garantiscono assenza di ogni bug.
Metodo e limiti: [PRODUCT_READINESS.md](PRODUCT_READINESS.md).

## Aggiornamento browser del 23 settembre 2026

Implementato `browse_source` con navigazione Chromium nativa, riferimenti di pagina
vincolati alla run e acquisizione dal DOM. La prova locale usa un server temporaneo:
un link generato da JavaScript conduce a un dettaglio salvato nel database.
La prova non è una ricerca reale Hermes né un test dei portali generalisti.

Il profilo dedicato è stato aggiornato sul server e verifica tutti e sette i tool,
incluso `browse_source`. API, worker e Hermes sono attivi. L'interfaccia è stata
pubblicata sul deployment di produzione.

La prima ricerca con browser è terminata in errore prima della raccolta: il provider
modello non ha risposto. Anche due richieste minime di inferenza hanno raggiunto il
timeout; il catalogo modelli risponde HTTP 200 e include il modello configurato.
Non è quindi una ricerca riuscita né prova di acquisizione multiportale.

Un test separato della fonte ha individuato una seconda causa di timeout: il
browser applicava la pausa di due secondi a ogni script e foglio di stile. La
correzione mantiene pausa sulle navigazioni/richieste dati, controlli host/robots e
budget di richieste; lascia caricare normalmente le dipendenze statiche. Il test
Chromium con 30 script verifica questa regressione. Dopo il deploy la verifica
live è riuscita: catalogo aperto, 10 link trovati nella prima pagina e un dettaglio
estratto. Il campione non include comune, zona e base della superficie; non è stato
importato. È prova del trasporto browser, non di una ricerca completata da Hermes.
Nove endpoint applicativi rispondono HTTP 200; gli asset UI pubblicati corrispondono
ai file verificati.

La programmazione ogni sei ore resta attiva. Le restrizioni dei portali non sono
rimosse dall'aggiornamento. Nessuna nuova copertura è dichiarata.

## Esito finale del 23 settembre

Il ciclo di ricontrollo è terminato `completed`: 28 link scoperti, quattro
acquisizioni/verifiche, due aggiornamenti, tre immobili compatibili e zero errori.
Le due fonti hanno risposto. Le modifiche ai campi mancanti provengono dalla nuova
acquisizione di Hermes, non da un aggiornamento manuale del database.

379 test Python passati, quattro integrazioni PostgreSQL saltate in questo passaggio;
controlli JavaScript, mappa, catalogo e processi superati. Collaudo autenticato live
su risultati, schede, immagini, priorità, calcoli economici temporanei, export Word
e consultazione OMI. Menu e schede corretti su mobile; testi ridotti.

## Collaudo aggiuntivo: scheduler e interazioni concorrenti

Un ciclo reale con trigger `schedule` è partito dal worker il 23 settembre alle
16:12 UTC e si è concluso alle 16:21 UTC: due cataloghi, 28 link, nessuna nuova
acquisizione e zero errori. Per il collaudo è stata anticipata una sola scadenza;
criteri, fonti e intervallo sono rimasti invariati. Il worker ha programmato il
ciclo successivo sei ore dopo la conclusione. La sessione browser non partecipa
alla pianificazione.

I ricontrolli obbligatori conservano un limite separato; gli annunci recenti della
stessa ricerca non consumano il budget per le novità. L'assenza di novità vale come
esito riuscito solo dopo il completamento del protocollo Hermes.

Collaudati su dati QA separati: risposta lenta dopo la chiusura del dialogo, cambio
di dialogo durante una richiesta, calcolo economico e salvataggio, rete assente e
ripristino, filtri rapidi, confronto di tre immobili, doppio clic sull'avvio manuale
e annullamento della coda. I contatori non riutilizzano i risultati precedenti in
caso di errore. Le fonti non collegate e i limiti del confronto OMI restano quelli
indicati sopra.
