# Flusso di ricerca e limiti dei dati

Il percorso operativo è: configura comune, zona o indirizzo e budget → seleziona
una fonte → avvia Hermes → verifica log e risultati → apri la scheda con fonte,
data di acquisizione e campi mancanti.

## Disponibile

- Hermes seleziona URL scoperti dalla fonte e richiede l'acquisizione; il backend
  verifica accesso, provenienza, formato, prezzi e criteri prima di salvare.
- La ricerca locale è testuale nei campi zona, indirizzo o titolo. Non risolve
  confini geografici né assegna una zona OMI per somiglianza di nomi.
- Prezzo, superficie, €/m², stato e dati disponibili restano distinguibili dai
  campi mancanti; lo stato ristrutturato viene normalizzato conservando l'evidenza.
- Deduplicazione, storico delle osservazioni, aggiornamento programmato e
  classificazione con citazioni hanno percorsi implementati e testati.
- Il motore del ranking separa completezza e score di approfondimento, espone
  la formula e richiede un benchmark compatibile per produrre sconto e score.

## Ancora da completare per una valutazione di zona

Il connettore corrente non fornisce per tutti gli annunci città, micro-zona,
base della superficie o foto riutilizzabili. Questi campi non vengono inventati.
Le foto non sono incluse nella raccolta fattuale attualmente configurata.

Non è attiva un'importazione automatica di quotazioni ufficiali. Il dataset
[OMI pubblicato dal Comune di Milano](https://dati.comune.milano.it/dataset/ds1996-quotazioni-immobiliari-omi-compravendita-e-locazione-riepilogo)
consultato il 21 settembre 2026 dichiara copertura fino al secondo semestre 2024:
la data di aggiornamento della pagina non equivale al periodo delle quotazioni.
Non è stato importato come riferimento corrente. OMI distingue inoltre superficie
netta e lorda; non sono convertite implicitamente in superficie commerciale.

Servono dati recenti con zona, tipologia, stato e base della superficie coerenti
con l'annuncio prima di attivare un confronto economico attendibile sul catalogo
live. Un prezzo medio degli annunci della stessa città non sostituisce questi dati.

Urbanistica avanzata, forecast e rendimenti non sono risultati verificati del
flusso. La copertura è quella delle fonti configurate, non dell'intero mercato.
