# Design engineering

Riferimento richiesto: `emilkowalski/skills`, skill `emil-design-eng`, revisione
`85e8e2363b713506e1d5b6e07a0eb2da66be1bc3` (MIT). I principi sono applicati alla UI,
non usati come istruzioni per accedere ai dati del cliente.

| Prima | Dopo | Motivo |
|---|---|---|
| Selettore demo/reale | Un solo workspace reale con onboarding | Nessuna ambiguità nei numeri mostrati al cliente. |
| Illustrazioni di immobili | Foto dell’annuncio consentite oppure placeholder esplicito | Non attribuire foto fittizie all’asset. |
| Panoramiche duplicate | `overview.js` con primitive in `ui.js` | Un punto di manutenzione per heading, metriche e miniature. |
| Stato worker in memoria API | Heartbeat condiviso persistente | La UI rileva anche il worker su processo distinto. |
| Indicatori senza contesto | Metodo, finestra, numerosità e dati mancanti | Un numero non supportato viene omesso. |
| Cambio vista che perde il focus | Ripristino del focus e selezione dell’input | Uso continuo da tastiera senza interruzioni. |

Inter configurato via CSS con fallback di sistema. Non distribuire file di font.
Palette blu/navy, contrasto e gerarchia del contenuto; successo/errore usano colori
semantici separati. Niente avatar di agenti, rendimenti, grafici o foto fittizi.

| Prima | Dopo | Motivo |
|---|---|---|
| Agente limitato al comune | Campo opzionale zona o indirizzo, salvato e visibile nella scheda agente | Rendere ripetibile una ricerca locale senza attribuire confini geografici non verificati. |
| Hermes riceveva soprattutto URL e prezzi | Breve testo della scheda fonte, normalizzato e senza duplicati | Selezionare candidati pertinenti prima di verificarne i dettagli. |

Il filtro locale cerca una dicitura nei campi zona, indirizzo e titolo. Le menzioni
di servizi vicini nella descrizione non bastano. Non modifica la micro-zona del
record, non geocodifica e non rende compatibili benchmark altrimenti diversi.

Le animazioni devono giustificarsi: transizioni brevi su proprietà esplicite, feedback
pressione e `prefers-reduced-motion`. Non animare conteggi come se fossero metriche
live quando non c’è una nuova osservazione. Le azioni da tastiera sono immediate.

Prima di una PR UI: controllare mobile, focus, stato vuoto, errore, caricamento,
contenuto lungo e dati incompleti. Non aggiungere librerie solo per un componente
che esiste già. Screenshot di collaudo popolati con fixture vanno marcati nel report;
le immagini pubblicate della release mostrano lo stato vuoto reale.

Fonte: https://github.com/emilkowalski/skills/tree/85e8e2363b713506e1d5b6e07a0eb2da66be1bc3

## Archivio 0.4

| Prima | Dopo | Motivo |
|---|---|---|
| Filtri sul campione in memoria | Catalogo server-side con conteggio e pagine | Il cliente trova anche i record più vecchi. |
| Selezione limitata alla pagina | Selezione fino a 100 ID tra pagine, confermata dal server | Il lavoro di revisione non viene perso cambiando pagina. |
| Salvataggi uno a uno | Dialogo di revisione multipla con riepilogo e nota | Controllo umano prima della mutazione; nessuna sovrascrittura dei ruoli/checklist. |
| Risposta di ricerca obsoleta | AbortController, generazioni di richiesta e debounce | I risultati vecchi non rimpiazzano quelli appena richiesti. |
| Focus perso durante un filtro | ID stabili e ripristino del focus su input/select | La navigazione da tastiera rimane prevedibile. |
| Numero senza provenienza storica | Timeline dei soli valori conservati e contesto valutario | Si distingue una variazione osservata da una supposizione. |

CSS dedicato `catalog.css`, primitive condivise di `ui.js`, azioni separate dalle viste.
Nessuna nuova dipendenza UI. Tabella e schede offrono la stessa selezione, il limite
è visibile. Gli errori sostituiscono le righe stale e conservano i filtri per correggerli.

| Prima | Dopo | Motivo |
|---|---|---|
| Benchmark solo da CSV | Consultazione OMI nazionale con selezioni provincia/comune/zona | Riutilizzare la stessa esperienza in territori diversi. |
| Mancanza di confronto quando la base della superficie è ignota | Riferimento ufficiale e scenari condizionati separati dallo score verificato | Mostrare informazioni utili senza nascondere le ipotesi. |
| Immagini non acquisite | Galleria della fonte autenticata e attribuita | Mostrare il bene reale mantenendo controlli su URL e contenuti. |

## Disponibilità e priorità

| Before | After | Why |
|---|---|---|
| Annuncio venduto tra le opportunità | Stato fonte visibile; filtro predefinito esclude chiusi e verifiche fallite | Evitare contatti e valutazioni su annunci non attivi. |
| Cerchio n.d. senza azione | Priorità operativa numerica con fattori espandibili | Distinguere dati utilizzabili da valutazione economica. |
| Foto prima delle informazioni decisionali | Prezzo, priorità e disponibilità prima della galleria | Rendere immediata la lettura della scheda. |
| Slogan e spiegazioni ripetute in ogni pagina | Titoli brevi; evidenze, caveat e metodo su richiesta | Ridurre il carico visivo senza togliere provenienza e limiti. |
| Frequenza in minuti e log tecnici | Ore, ultima verifica, prossima esecuzione | Far capire quando la ricerca torna a controllare il mercato. |

## Navigazione e stato delle ricerche

| Before | After | Why |
|---|---|---|
| Un agente con ultima run fallita appare solo attivo | Stato «Verifica fallita» e data dell'ultimo tentativo | Distinguere programmazione da acquisizione riuscita. |
| Nessun annuncio disponibile ripropone la configurazione iniziale | Collegamenti alle ricerche e alle fonti | Conservare il contesto del workspace già configurato. |
| Avviso tecnico permanente in Fonti | Conteggio fonti verificate e non accessibili; errori espandibili | Mostrare prima lo stato, poi la diagnosi. |
| Notifiche uguali sovrapposte | Un solo messaggio per testo | Lasciare leggibile il contenuto su mobile. |

| Before | After | Why |
|---|---|---|
| Zero annunci anche prima della raccolta | Trattino fino al primo conteggio | Distinguere assenza di risultati da ricerca non ancora eseguita. |
| Attesa del modello indistinguibile dal lavoro sulle fonti | Stato «In attesa di Hermes» e ultimo aggiornamento | Rendere visibili le attese lunghe senza simulare avanzamento. |
| Log con nomi interni delle operazioni | Etichette italiane e azione «Interrompi» | Ridurre il gergo nel percorso della ricerca. |

| Before | After | Why |
|---|---|---|
| Menu mobile chiuso ancora esposto alla tastiera | Menu nascosto anche dall'albero accessibile | Evitare focus e azioni su collegamenti fuori schermo. |
| Agenti manuali e ricerca online indistinguibili | Ricerca online per prima; modalità esplicita e stato Manuale/Programmato | Rendere chiaro quale agente trova nuovi annunci. |
| Superficie minima 0 m² e avvisi ripetuti negli stati vuoti | Nessun minimo; una sola indicazione operativa | Togliere rumore mantenendo il significato dei filtri. |
| Schede agenti più larghe del viewport | Colonna comprimibile e azioni su più righe | Tutti i comandi raggiungibili a 393 px |
| Segnaposto foto letto insieme all'immagine | Nascosto anche per tecnologie assistive a caricamento riuscito | Nessuna informazione contraddittoria |
| Località mancanti ripetute nell'intestazione | Mostrati solo i dati presenti; assenze nella sezione Dati | Titolo più leggibile senza nascondere lacune |
| Invito a leggere ipotesi OMI anche quando assenti | Messaggio breve sui dati non confrontabili | Evita un rimando senza contenuto |
