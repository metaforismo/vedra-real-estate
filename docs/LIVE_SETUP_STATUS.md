# Verifiche della ricerca guidata da Hermes

Revisione applicativa verificata: `4e58b20`. Collaudo del 21 settembre 2026.

## Flusso end-to-end

Esecuzione avviata dalla dashboard e completata dal runtime remoto reale:

| Controllo | Risultato |
| --- | --- |
| Link trovati nella fonte configurata | 20 |
| Annunci acquisiti dalla fonte | 3 |
| Nuovi record | 0 |
| Record aggiornati | 3 |
| Compatibili con i criteri | 3 |
| Errori | 0 |

Gli eventi documentano ricerca e acquisizione richieste da Hermes, seguite da
persistenza, analisi e completamento. La nuova lettura conserva gli identificativi
senza creare duplicati. Le modifiche includono immagini e riferimenti territoriali;
non provano una variazione reale di prezzo. Lo storico dei prezzi è coperto dai test.

La ricerca copre una fonte HTML configurata, non l'intero mercato. L'aggiornamento
giornaliero è configurato con prossima esecuzione salvata; la futura esecuzione
programmata non è ancora osservata.

## Riferimenti OMI nazionali e immagini

- Sincronizzato il catalogo ufficiale: 103 voci provinciali OMI e 7.890 codici
  comunali unici. Sono classificazioni della fonte, non un censimento aggiornato
  delle suddivisioni amministrative. Le quotazioni si acquisiscono su richiesta.
- Consultazione reale riuscita per Milano, Bari e Cosenza, semestre 2025/2,
  rispettivamente con 43, 33 e 9 zone. Il percorso UI live è verificato per Bari.
- Su un annuncio acquisito da Hermes: punto pubblicato dalla fonte intersecato
  con il poligono OMI D12, distanza dal confine 61,2 m. La posizione dell'indirizzo
  non è certificata; la scheda espone questa limitazione.
- Stessa scheda: 20 URL immagine rilevati, sei immagini servite con HTTP 200 e
  visualizzate nel browser con dimensioni effettive maggiori di zero.
- Sei confronti condizionati calcolati dalle quotazioni ufficiali e dalla superficie
  dichiarata. Tipo, stato, base della superficie e posizione rimangono ipotesi
  visibili: non alimentano automaticamente sconto e score verificati.
- Fonte, semestre e acquisizione accompagnano le tabelle. Nessun dataset sintetico
  è presentato come quotazione reale; cache e dati acquisiti rimangono fuori da Git.

La copertura nazionale riguarda i riferimenti OMI. Non implica disponibilità di
annunci acquisibili in ogni comune: occorre configurare una fonte utilizzabile.
Non tutti gli annunci pubblicano coordinate o caratteristiche sufficienti.

## Controlli

- Suite Python: 335 passati; quattro PostgreSQL esclusi dalla suite locale e poi
  passati su un database PostgreSQL temporaneo separato da quello operativo.
- Dopo l'aggiunta della regressione sull'indice della galleria: 11 test mirati
  media/OMI passati. La suite completa non è stata ripetuta dopo quel solo test.
- 15 moduli JavaScript, 8 controlli mappa, 7 test catalogo, 7 controlli processi
  e 18 scenari UI locali passati. Le fixture restano limitate al collaudo.
- Live: accesso, avvio ricerca, log persistente, consultazione OMI, immagini,
  dettaglio con analisi/provenienza e apertura dei confronti condizionati.
- Mobile a 393 px: documento e dialogo senza overflow orizzontale; le tabelle
  conservano lo scorrimento orizzontale interno.
- Esportazioni CSV/Excel: tre risultati corrispondenti al filtro dei criteri.
- Endpoint autenticati di workspace, operations, catalogo, insight, readiness,
  notifiche, agenti e fonti: HTTP 200. Bridge pubblico: HTTP 404.

## Correzioni già verificate

Il filtro locale dell'agente conserva zona/indirizzo nei criteri e nel contesto
fornito a Hermes. Stati espliciti sono normalizzati conservando il testo originale;
negazioni e condizioni ambigue rimangono sconosciute. La ricerca locale precedente
ha selezionato un annuncio su 20 link, senza errori o duplicati.

Sono verificati anche la query PostgreSQL della dashboard, l'aggiornamento dei
contatori durante la raccolta e la conservazione del proprietario dei file privati
quando il setup privilegiato effettua una sostituzione atomica.

Questi controlli verificano i percorsi descritti, non garantiscono assenza di ogni bug.
URL privati, indirizzi delle VM, account, credenziali e identificativi operativi
sono conservati fuori dal repository e dalla descrizione della PR.

Per metodi e limiti, vedi [Flusso di ricerca e limiti dei dati](PRODUCT_READINESS.md).
