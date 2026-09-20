# Ricerca, geografia e confronto economico

Il percorso operativo è: configura comune, zona o indirizzo e budget → seleziona
una fonte → avvia Hermes → verifica log e risultati → apri la scheda con fonte,
data di acquisizione, immagini e confronto territoriale.

## Quotazioni nazionali

Con `OMI_ENABLED=true`, il connettore consulta la
[Banca dati OMI su GeoPOI](https://www1.agenziaentrate.gov.it/servizi/geopoi_omi/index.htm).
Province, comuni, perimetri e quotazioni provengono dalle risorse pubbliche usate
dalla consultazione ufficiale, senza account, chiavi copiate o endpoint riservati.
Non è una API con SLA: un cambio di formato o un blocco della fonte resta un errore
visibile, non genera valori sostitutivi. Il connettore applica SafeFetcher con
host fisso, verifica robots, DNS pubblico, limiti dimensionali e richieste cadenzate.

La pagina Benchmark permette di scegliere provincia, comune, zona e destinazione.
Il semestre viene rilevato dalla fonte, non fissato nel codice. Alla verifica del
21 settembre 2026 il servizio restituisce 2025/2 come periodo più recente. Le
tabelle distinguono tipologia, stato OMI e base netta/lorda originali.

Il catalogo territoriale nazionale si prepara come utente del servizio:

```sh
python scripts/sync_omi.py --national
```

In alternativa `--province XX` limita la sincronizzazione. Dati e metadati sono
conservati in `DATA_DIR/market-cache`, fuori dal repository. Periodi: cache 24 ore;
cataloghi, perimetri e tabelle: 30 giorni. Le risorse scadute vengono aggiornate
alla consultazione; un errore non promuove la cache scaduta a dato corrente.
Non si scarica in blocco l'intero archivio nazionale delle quotazioni.

## Localizzazione

Le coordinate JSON-LD o un singolo marker WDK pubblicato nella pagina permettono
l'intersezione con i poligoni ufficiali del comune e semestre identificati.
Anelli, buchi e geometrie multiple sono gestiti; un punto ambiguo o a meno di
20 metri da un confine non riceve un'assegnazione. Il risultato verifica la zona
del punto pubblicato, non certifica la precisione dell'indirizzo dell'immobile.

Non si assegna una zona per somiglianza di nomi. Senza coordinate o comune
univoco la scheda spiega perché il riferimento non è disponibile. Il criterio
testuale zona/indirizzo dell'agente rimane distinto dal perimetro OMI.

## Confronto e stime condizionate

Le quotazioni OMI sono intervalli territoriali, non prezzi osservati di singole
transazioni. La scheda riporta separatamente fonte, periodo, acquisizione e
localizzazione. Per ogni tipologia/stato pertinente espone un confronto condizionato:

- range teorico = superficie dichiarata × estremi OMI;
- scostamento = (prezzo richiesto al m² / punto medio OMI − 1) × 100;
- ipotesi: tipologia, stato OMI, base della superficie e posizione corretti.

Non esiste conversione implicita commerciale/lorda/netta. Le ipotesi sono visibili;
lo scostamento non viene chiamato rendimento o sconto accertato. L'incertezza è
non calibrata: il range OMI non è un intervallo di confidenza statistico. Riferimenti
futuri o oltre 18 mesi non producono scenari correnti. Non sono usati moltiplicatori
inventati né un dataset sintetico spacciato per mercato reale.

Score e sconto verificati restano distinti dagli scenari e richiedono i metadati
omogenei del motore benchmark. Completezza non significa accuratezza.

## Immagini e raccolta

`retain_images` abilita separatamente i riferimenti alla galleria della fonte.
L'estrattore seleziona le immagini dell'annuncio, non loghi arbitrari. Il proxy
richiede sessione, URL registrata e host in `IMAGE_ALLOWED_DOMAINS`; verifica
robots, formato raster, dimensioni, cache e backoff. La galleria mostra fino a sei
immagini originali con attribuzione e collegamento alla fonte. Il workspace non
acquisisce una licenza di redistribuzione per il solo fatto di leggere la pagina.

Hermes sceglie candidati e interpreta evidenze; fetch, estrazione, geografia,
calcoli e persistenza rimangono deterministici. La copertura degli annunci dipende
dalle fonti collegate: copertura nazionale OMI non significa annunci disponibili
in ogni comune. Urbanistica, forecast e rendimenti non sono certificati dal flusso.
