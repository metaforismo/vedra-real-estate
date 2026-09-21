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

## Disponibilità, controlli ricorrenti e priorità

La disponibilità della fonte è distinta dallo stato di revisione del team. Le
indicazioni strutturate e il titolo possono chiudere un annuncio; se le immagini
sono autorizzate, il connettore controlla le prime due con Tesseract. Il controllo
OCR isola e raddrizza le fasce rosse dei cartelli, poi prova cinque orientamenti
della pagina. Conserva parola, confidenza OCR, regione, hash, URL e data. Una fascia
non leggibile o una parola di stato con bassa confidenza richiede verifica e non
viene promossa ad annuncio attivo.
La confidenza OCR non è probabilità di vendita. Immagini mancanti o illeggibili
richiedono verifica; immagini successive alla seconda non sono controllate.
Un riscontro debole non riapre automaticamente un annuncio già chiuso.

Le ricerche periodiche sono eseguite dal worker persistente anche a browser chiuso.
Hermes riceve prima gli annunci già osservati da ricontrollare, inclusi quelli
spariti dal catalogo, poi candidati nuovi ordinati prima di quelli già conosciuti.
La chiusura della raccolta è impedita se rimangono ricontrolli obbligatori. Ogni
fonte ha limiti separati e finiti per aggiornamenti e acquisizioni. HTTP 404/410
richiede verifica: non viene interpretato come vendita o blocco dell'intera fonte.
La ricerca è periodica sulle fonti configurate, non un feed universale in tempo reale.

La priorità `triage/1.0` è un indice operativo: dati 30 punti; disponibilità 20
(di cui solo 10 per una pagina pubblicata, non confermata); confronto economico 40
(10 se disponibile soltanto un confronto OMI condizionato); strategie documentate
10. Annunci chiusi o con verifica fallita hanno priorità zero. Il confronto omogeneo
usa clamp(20 + sconto_percentuale × 0,8; 0; 40). La priorità non è un prezzo stimato,
una probabilità di rendimento o un sostituto della due diligence. Score economico
preesistente e delta rimangono distinti anche nelle esportazioni.

Per il controllo immagini installare `tesseract-ocr` dal registro di pacchetti del
sistema. Pillow è una dipendenza applicativa; non sono necessarie API OCR esterne.
