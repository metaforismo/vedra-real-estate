# Verifiche live

Collaudo del 21 settembre 2026. Dati operativi e credenziali restano fuori dal repository.

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

Il runtime live risponde e la sua ultima ricerca sulla fonte configurata risulta
completata senza errori. Espone ancora i sei tool precedenti. L'aggiornamento al
nuovo profilo a sette tool e il collaudo live del browser sono in attesa del
ripristino della sessione amministrativa. Nessuna nuova copertura multiportale
è dichiarata e nessuna credenziale personale è conservata nel repository.
