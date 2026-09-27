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

## Collaudo delle risposte lente e dei cicli periodici

| Before | After | Why |
|---|---|---|
| Una risposta tardiva riapre la scheda chiusa | Caricamento annullabile; risposte legate alla schermata che le ha richieste | Chiusura e navigazione restano definitive. |
| Il polling può scrivere nel dettaglio di un'altra ricerca | Una sola richiesta di stato alla volta, con controllo dopo la risposta | Nessuna mescolanza di log o risultati. |
| Il calcolo di uno scenario chiuso accede a elementi rimossi | Risultati ed errori restano nel form originario | Evita errori e modifiche alla scheda successiva. |
| Una fonte riuscita e una fallita risultano solo «Programmato» | Stato «Verifica parziale» | Rende evidente la copertura incompleta. |
| Catalogo verificato senza novità marcato fallito | Esito riuscito solo dopo raccolta e analisi concluse | L'assenza di novità non è un guasto. |
| Annunci recenti consumano il limite delle nuove acquisizioni | Nuovi candidati per primi; ricontrolli dovuti separati | Le ricerche successive trovano novità invece di ripetere il lavoro. |

| Before | After | Why |
|---|---|---|
| Errore di rete con conteggio della ricerca precedente | Conteggio indisponibile, paginazione e selezione pagina disabilitate | Non attribuisce vecchi dati al nuovo filtro. |
| Errore del browser in inglese | Messaggio breve in italiano con Riprova | Rende il recupero comprensibile. |
| Intestazioni e dettagli tecnici ripetuti nei dialoghi | Titoli essenziali, motore e frequenza leggibili | Ogni parola aiuta a capire o compiere un'azione. |

## Configurazione dei portali

| Before | After | Why |
|---|---|---|
| Collegamento interamente manuale | Preset per Immobiliare.it, idealista e Casa.it | Riutilizza configurazioni pubbliche senza inventare autorizzazioni o accesso. |
| Selettori e JSON sempre esposti | Impostazioni di acquisizione apribili | Nome, ricerca e consenso restano leggibili su mobile. |
| Test fonte presentato come JSON | Esito, campione e campi mancanti; dettagli tecnici separati | Distingue un accesso negato da un catalogo verificato. |
| Tentativo fallito etichettato «Verificata» | «Controllata» | La data non implica un esito positivo. |

## Disponibilità e importazioni

| Before | After | Why |
|---|---|---|
| Pipeline senza disponibilità | Badge e filtro separato dalla fase del team | Venduto non significa pratica conclusa; lo storico rimane accessibile. |
| Ricerca vuota mostra sette colonne vuote | Messaggio e Azzera filtri | Recupero immediato senza perdere funzioni. |
| Importa benchmark apre CSV immobili | Tipo benchmark preselezionato | Mantiene il contesto dell'azione. |
| Totale Immobili ambiguo | Annunci in archivio | Il totale comprende anche lo storico. |

## Dalla ricerca alla selezione

| Before | After | Why |
|---|---|---|
| Criteri soltanto numerici | Istruzioni qualitative per ogni ricerca, esito con citazioni | Permette preferenze specifiche senza confonderle con fatti o superare i filtri. |
| Un solo riferimento economico | Da ristrutturare, ristrutturato, nuovo e OMI separati | Rende visibili campione, compatibilità e assenze. |
| Ristrutturato normalizzato come buono | Stato distinto, solo su dichiarazione esplicita | Evita confronti tra categorie diverse. |
| Word come prima uscita della scheda | Excel principale, Word disponibile | Facilita confronto, filtro e passaggio al team. |
| Export concentrato sui campi tecnici | Selezione iniziale, riferimenti, comparabili, criteri e storico in fogli distinti | Il primo foglio serve per decidere cosa approfondire; gli altri permettono la verifica. |
| Istruzioni visibili soltanto nella configurazione | Dettaglio apribile nell’agente e nello screening | Mantiene la pagina breve senza perdere i criteri applicati. |

## Decisioni e contatti · sviluppo locale

| Before | After | Why |
|---|---|---|
| Metriche e panoramica come prima schermata | Oggi: immobile, motivo, recapito e prossimo passo | Riduce il percorso tra ricerca e contatto. |
| Molte sezioni equivalenti | Oggi, Immobili, Ricerche, Lavorazione; Gestione apribile | Semplifica la navigazione senza eliminare funzioni. |
| Prompt unico per tutto | Criteri di selezione e istruzioni di ricerca distinti | Separa cosa deve qualificarsi da come cercarlo. |
| Risultato AI complessivo | Esito e citazioni per requisito | Rende visibili i criteri ignorati o non documentati. |
| Un nome broker può sembrare un mandato verificato | Inserzionista dichiarato separato dalla verifica umana | Non confonde un contatto con la sua autorità sul bene. |
| Note senza prossimo passo | Esito contatto, richiamo, autore e storico | Evita di richiamare subito chi è già stato gestito. |
| Pannello archivio richiuso dopo un salvataggio | Stato aperto conservato durante aggiornamenti | Mantiene il contesto di lavoro. |
| Data di richiamo con ora e senza anno | Data completa, senza ora | Il richiamo è una giornata, non un appuntamento orario. |
| Moduli JS senza versione conservati in cache | Rivalidazione degli asset | Evita mescolanze fra interfaccia nuova e azioni vecchie. |

Riutilizzati dialoghi, guardie per richieste asincrone, focus, tema e riduzione del movimento. Nessuna animazione decorativa aggiunta. Desktop e 393 px verificati su backend locale e dati QA.


## Evidenze per decidere · confronto tra fonti

| Before | After | Why |
|---|---|---|
| Annunci dello stesso asset separati | Dossier apribile con dati e recapiti di ogni fonte | Riduce il lavoro di confronto senza scegliere arbitrariamente un prezzo vero. |
| Due annunci selezionati producono due contatti | Un candidato per asset confermato e richiami condivisi | Evita lavoro duplicato. |
| Disponibilità discordante poco evidente | Avviso e verifica prima del contatto | Non presenta un possibile venduto come pronto da chiamare. |
| Mediana senza composizione del campione | Numero fonti, date, quartili, concentrazione e dispersione | Aiuta a capire quanto approfondire prima di usare il numero. |
| OMI senza valori nella sintesi | Fasce, stato, superficie e periodo visibili | Porta i quattro riferimenti nello stesso punto. |
| Avviso generico di confronto insufficiente sopra campioni utilizzabili | Campioni per primi; benchmark di screening in un dettaglio distinto | Evita di confondere l’assenza del benchmark configurato con l’assenza di dati. |
| Tabella OMI e spiegazioni sempre aperte | Tabella e metodo apribili | Conserva il contenuto, riduce rumore e scorrimento. |
| Excel senza differenze tra portali | Nono foglio con fonti dello stesso asset | Rende verificabile il confronto fuori dalla piattaforma. |

Verificati desktop, mobile 393 px, tema scuro, apertura/chiusura e passaggio fra
annunci collegati. Nessuna animazione aggiuntiva: mantenuti focus, dialoghi e
preferenza di movimento ridotto. Tutte le schermate di collaudo usano dati QA.


## Filiera e decisione economica

| Before | After | Why |
|---|---|---|
| Un recapito non spiega il ruolo sul bene | Filiera dichiarata con citazione e requisito configurabile | Distingue un contatto dal rapporto dichiarato con la proprietà. |
| Prezzo in linea può rientrare nella nuova ricerca | Opzione Solo sotto benchmark preselezionata e modificabile | Rende esplicita la ricerca di un vantaggio di prezzo. |
| Stesso asset con più broker trattati allo stesso modo | Precedenza al recapito diretto dichiarato | Riduce i passaggi senza attribuire mandati verificati. |
| Scenario con solo ROI e sensibilità fissa | ROI obiettivo, tetto d’acquisto e stress combinato modificabile | Aiuta a decidere se e quanto negoziare. |
| Vecchio risultato resta dopo una modifica | Risultato invalidato; risposte tardive scartate | Mantiene coerenti input e numeri mostrati. |
| Export singolo senza scenari | Scenari salvati esportati dallo stesso calcolatore della UI | L’Excel è un riepilogo, non una funzione separata. |

Desktop e 393 px verificati; nessuna animazione aggiunta ai calcoli ripetuti. I campi
mantengono etichette accessibili e gli errori non eliminano le ipotesi immesse.

## Preparazione del contatto

| Before | After | Why |
|---|---|---|
| Un dato vecchio può restare pronto da chiamare | Scadenza coerente con il ricontrollo della fonte; passaggio a verifica | La data del catalogo non sostituisce il controllo del dettaglio. |
| Esito su un annuncio collegato non visibile nella scheda | Riepilogo con rimando al contatto originale | Evita doppio lavoro conservando il contesto del broker contattato. |
| Dati mancanti sparsi nella scheda | Domande pertinenti sotto “Da chiarire” | Aiuta a preparare il contatto senza aggiungere testo sempre visibile. |
| Scadenza senza origine del dato | Importazione o pagina acquisita, data e stato | Non confonde una nuova importazione con una verifica indipendente. |
| Riepilogo Excel senza queste verifiche | Stessi avvisi e domande, annuncio di origine per il contatto | Conserva la parità fra interfaccia ed export. |

Riutilizzati dettagli HTML, pulsanti e dialoghi esistenti. Nessuna nuova animazione.

## Scheda immobile · gerarchia e spaziature

| Before | After | Why |
|---|---|---|
| Word spinto a destra da `nth-last-child`, Excel mescolato alla selezione | Gruppo export esplicito, Excel e Word affiancati | La vicinanza riflette la funzione; non dipende dal numero di pulsanti. |
| Prezzo dopo tutto il dossier contatto | Prezzo e priorità subito dopo titolo e località | Si comprende l’asset prima di leggere le verifiche. |
| Margini di toolbar e sezioni sommati | 8 px nei gruppi, 12 px tra righe, 20/24 px tra sezioni | Ritmo unico, nessuno spazio accidentale. |
| Fonte mescolata ai file scaricabili | Fonte nella riga degli strumenti | Distingue consultazione esterna ed esportazione. |
| Grafico circolare per una priorità operativa | Valore compatto con metodo apribile | Conserva score e fattori riducendo l’enfasi visiva. |
| Foto prima dei riferimenti decisionali | Contatto e quattro riferimenti prima di foto e analisi | Ordine coerente con ricerca del contatto e valutazione. |
| Dialogo mobile limitato dalla larghezza massima del browser | Scheda a tutta larghezza, export affiancati e controlli da 44 px | Recupera spazio utile e rende i comandi toccabili. |
| Intestazione storico deborda a 320 px | Titolo, azione e conteggio possono andare a capo | Conserva ogni comando senza scorrimento orizzontale. |

Nessuna nuova animazione: queste sono letture e azioni frequenti. Mantenuti focus,
Escape, movimento ridotto e metodi apribili da tastiera. Nessuna funzione rimossa.

## Reference visiva · percorso operativo

Reference raster generata con lo strumento imagegen integrato (modalità `ui-mockup`).
Output e prompt completi conservati localmente in `artifacts/design-reference/`.
La reference è materiale di progettazione con dati illustrativi: nessun nome,
annuncio, contatto o valore generato viene importato nel prodotto. L’interfaccia è
HTML/CSS accessibile, non un’immagine inserita al posto delle funzioni.

| Before | After | Why |
|---|---|---|
| Oggi con testo e azioni distribuiti su una scheda generica | Colonne immobile, motivi, contatto e azioni; righe adattive su mobile | Confronto visivo immediato, un punto stabile per aprire la scheda. |
| Provenienza e stato del servizio sempre ripetuti | Provenienza per riga apribile, stato esteso in Archivio e attività | Conserva le verifiche senza sottrarre spazio ai candidati. |
| Modulo di ricerca senza gerarchia | Tre gruppi: Asset, Criteri, Ricerca | Ogni campo ha un ruolo chiaro nel flusso. |
| Prompt dopo molti filtri | Criteri personali evidenti e istruzioni Hermes separate | Distingue cosa selezionare da dove e come cercare. |
| Filtri secondari sempre esposti | Filtri avanzati apribili con conteggio aggiornato | Riduce il testo senza perdere o azzerare configurazioni. |
| Campo non valido in dettaglio chiuso | Apertura automatica prima del focus della validazione nativa | Evita un salvataggio bloccato senza una correzione visibile. |
| Termini agente e ricerca alternati per la stessa azione | Nuova ricerca, Configura ricerca, Salva ricerca | Lessico coerente dal punto di vista dell’utente. |
| Contatto, verifiche e mercato visivamente uniformi | Blocchi distinti; catasto e storico apribili | Mantiene evidenze e limiti, dà precedenza a contatto e confronto. |
| Aiuto generico rimanda a candidati inesistenti | Stato vuoto coerente con i candidati da verificare | Nessun rimando senza contenuto. |

`workflow.css` contiene la composizione delle tre superfici. Restano condivisi i
controlli esistenti; nessuna libreria o nuova animazione decorativa. Nel modulo,
header e footer restano raggiungibili, i campi hanno etichette e i dettagli sono
utilizzabili da tastiera. Gli errori conservano prompt e filtri.

## Esito della ricerca e criteri AI

| Before | After | Why |
|---|---|---|
| Registro completo appena aperta una ricerca | Esito, conteggi osservati e analisi mancanti; registro apribile | Capire prima cosa è successo, poi approfondire. |
| Annunci elaborati chiamati verificati | Elaborati; risposte AI accettate distinte dalle opportunità | Non equipara acquisizione, validazione del contratto e correttezza del modello. |
| Ogni aggiornamento richiude i dettagli | Apertura, focus e scorrimento conservati | Permette di leggere le istruzioni mentre arriva un nuovo evento. |
| Prompt, esito e citazioni ripetuti | Stato per requisito, citazioni apribili, sintesi separata | Conserva le evidenze e rende riconoscibili i requisiti incerti. |
| Criteri dopo dati e storico | Criteri subito dopo i riferimenti di mercato | Tiene vicini confronto economico e motivi della selezione. |
| Risultati accessibili tornando alla pagina precedente | Azione Risultati attuali della ricerca | Accorcia il percorso, chiarendo che non è un archivio storico dell’esecuzione. |
| Stato fallito senza task ancora in attesa | Raccolta non completata; nessun rapporto 0/0 | Mostra il limite effettivo senza suggerire attività inesistente. |
| Interruzione proposta anche alla sola lettura | Comando disponibile soltanto agli editor | Evita azioni che il server respingerebbe. |

Componente `run-ui.js`, primitive condivise e disclosure native. Nessuna nuova
animazione decorativa; griglia 2×2 sotto 600 px, test fino a 320 px. I conteggi AI
provengono dai task della singola esecuzione; una risposta respinta non li incrementa.
Le istruzioni mostrate sono quelle salvate all’avvio, non la configurazione attuale.

## Archivio · filtri, selezione ed export

| Before | After | Why |
|---|---|---|
| Etichette dei filtri solo per lettori di schermo | Etichette visibili, griglia adattiva e altezze coerenti | Il valore scelto conserva il proprio contesto. |
| Excel in alto esporta implicitamente la selezione precedente | Esporta risultati in alto; Esporta selezione nella barra | Azione e contenuto del file coincidono anche cambiando i filtri. |
| Confronto disponibile con qualsiasi numero di record | Attivo con 2–3 immobili, istruzione breve negli altri casi | Previene errori senza eliminare il controllo server. |
| Barra nascosta ancora raggiungibile da tastiera | `inert` quando non ci sono selezioni | Il focus segue solo i comandi disponibili. |
| Grande riquadro vuoto per ogni foto mancante | Testata compatta da 64 px, anche dopo un errore immagine | Riduce lo spazio improduttivo senza inventare immagini. |
| Percentuale nella scheda senza riferimento esplicito | Scarto accompagnato da “vs benchmark” | Non suggerisce margine o probabilità di profitto. |
| Stato vuoto con istruzioni generiche | Azzera filtri o Nuova ricerca, secondo contesto e ruolo | Fornisce il prossimo passo senza proporre azioni non autorizzate. |
| Toast sovrapposti alla selezione e barra animata a ogni click | Toast in alto durante la selezione; barra immediata | Le conferme non nascondono le azioni frequenti. |
| Controlli della selezione piccoli su mobile | 44 px, ritorno a capo e spazio finale riservato | Ogni azione rimane raggiungibile fino a 320 px. |

Riutilizzate primitive, palette e disclosure esistenti. Nessuna nuova animazione:
filtrare e selezionare sono operazioni frequenti. Le prove visive usano esclusivamente
il database temporaneo della suite UI, senza modificare la scheda operativa dell’utente.

## Lavorazione · incarichi e revisione

| Before | After | Why |
|---|---|---|
| Bacheca orizzontale come unica vista; una colonna può allungare tutta la pagina | Elenco operativo iniziale e bacheca alternativa con colonne a scorrimento | Confronto rapido senza rimuovere le fasi. |
| Responsabile e scadenza nascosti nelle schede | Colonne dedicate; filtri per fase, responsabile, scaduti e assegnazioni | Individua il lavoro da prendere in carico. |
| Conteggio senza avviso sul campione caricato | Vista parziale esplicita quando il workspace supera il limite | Non presenta i record caricati come archivio completo. |
| Cambio vista perde il focus | Focus ripristinato su Elenco/Bacheca e filtri rapidi | Uso continuo da tastiera. |
| Checklist conteggia ogni chiave presente | Conteggio delle cinque verifiche previste | Campi estranei non aumentano il progresso. |
| Revisione modificabile durante il salvataggio | Campi bloccati durante la richiesta HTTP | Le modifiche successive non vengono perse alla chiusura. |
| Fase e versione lette da risposte distinte | Un'unica lettura del record di lavoro | Evita di salvare una fase obsoleta con una versione più recente. |
| Responsabile non più assegnabile ricade sul valore vuoto | Valore precedente conservato e segnalato | Nessuna cancellazione implicita del responsabile. |
| Conflitto con il collega richiede chiusura e riapertura manuali | Modifiche locali conservate; ricaricamento esplicito e annullabile | Nessuna sovrascrittura silenziosa. |

`pipeline-ui.js` raccoglie elenco, bacheca e modulo di revisione. Riutilizza le
primitive e i valori esistenti; nessuna animazione decorativa. Il layout mobile
mantiene etichette e comandi da 44 px. Fase del team e disponibilità dell’annuncio
restano distinte; una revisione conclusa non viene segnalata come scaduta.

## Scenario economico · ipotesi, risultati e salvataggio

| Before | After | Why |
|---|---|---|
| Dodici campi con la stessa gerarchia | Gruppi Operazione e Costi; stress modificabile in una disclosure | Riduce la prima lettura conservando tutte le ipotesi. |
| Risultati sotto il modulo | Pannello affiancato su desktop, sequenziale su mobile | Rende immediato il confronto tra ipotesi e risultato. |
| Risultati e cautele mescolati | Risultato, ROI, prezzo massimo e stress visibili; sensibilità e metodo apribili | Priorità ai dati della decisione, senza nascondere le condizioni del calcolo. |
| Chiusura fuori schermo durante lo scorrimento | Intestazione fissa e contenuto scorrevole | Mantiene sempre un'uscita visibile con bersaglio da 44 px. |
| Calcola e Salva sotto un modulo lungo | Comandi visibili durante la compilazione | L'azione successiva resta raggiungibile; il focus va al titolo dei risultati. |
| Salvataggio ricrea il modulo ai valori iniziali | Stessi valori e risultati restano aperti; Salva copia esplicito | Non interrompe la valutazione e chiarisce che gli scenari sono snapshot. |
| Rinominare cancella il risultato | Solo i campi economici invalidano il calcolo | Un nome diverso non modifica i numeri. |
| Apertura di uno scenario sostituisce subito la bozza | Conferma annullabile quando ci sono modifiche | Previene la perdita delle ipotesi in lavorazione. |
| Azioni concorrenti e risposta tardiva poco chiare | Calcola e Salva bloccati durante la richiesta; revisioni distinte per nome e numeri | Un risultato precedente non viene attribuito a nuove ipotesi. |
| Cancellazione ricrea la finestra | Aggiornato soltanto l'elenco; bozza conservata | Rimuovere uno snapshot non cancella ciò che si sta valutando. |

`scenario-ui.js` raccoglie presentazione e definizioni dei campi. Calcoli e
validazioni restano nelle API esistenti. Il prezzo in valuta diversa da EUR non
precompila un'ipotesi in euro; massimali monetari e percentuali mantengono i
centesimi. Nessuna nuova animazione decorativa, modello probabilistico o stima
di mercato. Test locali con fixture separate dai dati operativi.

## Contatti · esito e prossimo passo

| Before | After | Why |
|---|---|---|
| Esito, autore, data e richiamo su una sola riga | Riepilogo con esito, interlocutore e prossimo contatto separati | Si legge cosa è accaduto e quando tornare sull'asset. |
| Catasto prima del riepilogo operativo | Ultimo contatto prima delle verifiche di dettaglio | Rispetta il percorso “chi chiamo e cosa devo chiarire”. |
| Citazione del mandato sempre estesa | Filiera visibile, dichiarazione della fonte apribile | Conserva la prova senza confonderla con la verifica del team. |
| Nessuna risposta come esito iniziale | Selezione esplicita obbligatoria | Previene registrazioni accidentali. |
| Richiamo e Non pertinente accettati insieme nel modulo | Richiamo disabilitato e non inviato; bozza della data conservata | Previene il conflitto e consente di cambiare idea senza riscrivere la data. |
| Verifica mandato spiegata solo dall'errore server | Aiuto contestuale quando si sceglie la verifica del team | Esplicita la documentazione richiesta, mantenendo la validazione server. |
| Campi modificabili durante il salvataggio | Fieldset e Annulla bloccati fino alla risposta | Il contenuto salvato coincide con quello visibile durante l'invio. |
| Errore vecchio visibile dopo la correzione | Messaggio rimosso alla modifica, ripresentato se il server rifiuta ancora | Evita di far sembrare invalida una correzione non ancora inviata. |
| Chiusura fuori vista su schermi stretti | Intestazione fissa, scorrimento del modulo, comandi da 44 px | Resta utilizzabile fino a 320 px. |

Nomi accessibili espliciti sui campi con aiuti e opzioni; note multilinea
conservate nello storico. Il modulo continua a usare l'identificativo idempotente
esistente: un esito registrato con risposta HTTP persa può essere reinviato
senza duplicarlo. La dichiarazione del broker resta distinta dal mandato
verificato dal team. Nessuna nuova animazione su questi controlli frequenti.

## Comparabili · campione e provenienza

| Before | After | Why |
|---|---|---|
| Avviso lungo prima dei dati; assenza del campione ripetuta | Due riferimenti affiancati, motivo del limite e metodo apribile | Distingue subito richiesta dell'immobile, mediana e dati insufficienti. |
| Elenco con prezzo e tempo relativo | Titolo apribile, fonte, data di rilevazione, superficie e prezzo | Ogni confronto è verificabile sul singolo record. |
| Regole proprie della finestra Comparabili | Servizio condiviso con i riferimenti di mercato | Evita di includere aste, disponibilità ignota, date future e asset discordanti. |
| Mediana solo sui primi 12 asset mostrati | Statistiche sull'intero campione valido entro il limite di 1.000 annunci; 12 righe mostrate | La dimensione dell'interfaccia non determina il risultato statistico. |
| Nessun contesto sul numero di fonti o sui limiti | Conteggi, avvisi e fascia centrale consultabili | Non confonde quantità, indipendenza e accuratezza dei dati. |
| Scarto da ricostruire manualmente | Richiesta sopra/sotto/in linea con la mediana | Rende leggibile il confronto tra richieste, senza chiamarlo margine o valore di mercato. |
| Excel senza il confronto omogeneo per stati diversi dalle tre categorie | Voce Stesso stato nei fogli Riferimenti e Comparabili | Mantiene il file coerente con il confronto mostrato in piattaforma. |
| Finestra stretta con controlli fuori vista durante lo scorrimento | Intestazione fissa, elenco adattivo e controlli mobile da 44 px | Mantiene provenienza e azioni raggiungibili fino a 320 px. |

`comparables-ui.js` separa la presentazione dal servizio `MarketReferences`.
Nessuna nuova animazione; disclosure nativa da tastiera. Le fonti con URL non
navigabile restano consultabili dalla scheda interna. La superficie è etichettata
come commerciale/lorda/netta; la data si riferisce alla rilevazione. Per gli
annunci all'asta non viene proposta una mediana di annunci ordinari. I campioni
di Stesso stato possono coincidere con una delle tre categorie: il file li
identifica distintamente, senza presentarli come ulteriori asset indipendenti.

## Inbox · aggiornamenti e destinazioni

| Before | After | Why |
|---|---|---|
| Il filtro Non lette esaminava solo gli ultimi 200 eventi | Filtro server e paginazione a cursore da 40 eventi | Anche una notifica vecchia resta raggiungibile. |
| Eventi senza distinzione | Filtri Nuovi immobili, Prezzo, Disponibilità e Fonti | Riduce il tempo per ritrovare il cambiamento pertinente. |
| Riga cliccabile anche senza destinazione | Apri immobile o Apri ricerca solo quando esiste il collegamento | Distingue navigazione e stato di lettura personale. |
| Conteggi, email e comandi sullo stesso piano | Filtri, conteggio e azioni separati; canali in disclosure | I dettagli operativi restano disponibili senza occupare il primo piano. |
| Nessuna gestione del caricamento incrementale | Stato occupato, errore contestuale e riprova sulla stessa pagina | Un errore di rete conserva i risultati già letti. |
| Pulsanti testuali con dimensioni da icona | Larghezza adattiva, hit area da 44 px e spazi coerenti | Evita sovrapposizioni e rende le azioni utilizzabili da mobile. |

Il comando globale specifica «l’intera Inbox», anche quando è attivo un filtro.
La lettura resta personale e idempotente; i record dimostrativi sono esclusi.
I cursori ordinano per data e ID, evitando duplicazioni durante nuovi inserimenti.
Le risposte superate da filtri, navigazione o logout non aggiornano l’interfaccia.
L’aggiornamento periodico del workspace non azzera le pagine già caricate: Aggiorna
ricarica esplicitamente la lista. I filtri recuperano il focus; all’ultima pagina
il focus passa ai risultati. Nessuna animazione decorativa aggiunta.

## Cronologia · cambiamenti leggibili e verificabili

| Before | After | Why |
|---|---|---|
| Prezzi nella scheda senza valuta, versione del parser in primo piano | Tre rilevazioni recenti con valuta originale; cronologia completa apribile | Rende utile l'anteprima senza mescolare valute o nascondere il resto dello storico. |
| Tutti i campi sullo stesso piano | Prezzo, disponibilità, superficie e descrizione prima; gli altri apribili | Accelera la lettura senza eliminare dati. |
| Ogni pagina sostituiva quella precedente | Aggiunta progressiva delle rilevazioni | Permette di seguire la sequenza conservando testi e dettagli già aperti. |
| Descrizioni troncate a 600 caratteri | Confronto integrale in disclosure | Mantiene accessibili le evidenze utili a una decisione. |
| Valori separati soltanto da una freccia | Colonne Prima/Dopo, impilate su mobile | Rende leggibile la direzione del cambiamento anche con testi lunghi. |
| Importi da confrontare mentalmente | Ribasso/aumento percentuale con contesto omogeneo | Evidenzia un cambiamento osservato; non lo chiama sconto di mercato. |
| Cronologia senza ritorno alla scheda | Titolo dell'immobile e Torna all'immobile | Mantiene il contesto e il percorso di valutazione. |
| Metadati tecnici e limiti sempre visibili | Dettagli rilevazione e metodo apribili | Conserva le informazioni riducendo il rumore iniziale. |

Il calcolo `observed_price_change` usa esclusivamente valori conservati: prezzi e
superfici positivi, valuta nota, stessa operazione, superficie e base di superficie.
È condiviso dalla cronologia API e dalla colonna Variazione % omogenea dell'Excel;
la UI non ricalcola percentuali. Nessuna ricostruzione dei campi storici mancanti.
La prima rilevazione è distinta dalla pubblicazione dell'annuncio.

Il caricamento incrementale conserva gli elementi del DOM e le disclosure aperte.
Un errore lascia le rilevazioni consultabili e consente Riprova; la chiusura della
finestra rende inapplicabile una risposta in ritardo. Controlli da 44 px, intestazione
fissa, spazi di 12/16/24 px e nessuna nuova animazione decorativa.


## Qualità dei dati · dai conteggi alla verifica

| Before | After | Why |
|---|---|---|
| Copertura calcolata sugli annunci caricati | Conteggi sull’intero archivio | Il limite di caricamento non altera i dati mancanti. |
| Barre senza destinazione | Vedi annunci per ogni campo mancante | Dal problema si arriva direttamente ai record da verificare. |
| Filtro nascosto nei controlli avanzati | Indicatore visibile e rimozione immediata | Rende comprensibile perché l’archivio mostra quella selezione. |
| Coppie di ID e comandi ravvicinati | Due fonti affiancate, prezzi allineati e decisioni separate | Consente di confrontare gli annunci prima di collegarli. |
| Coppie già valutate nella stessa lista | Da verificare e Già valutati | Distingue il lavoro restante dalle decisioni reversibili. |
| Regole sempre in primo piano | Metodo e limiti apribile | Conserva il contesto senza ostacolare le azioni. |

Tre indicatori con pari larghezza e spazi di 24 px. Campi ordinati per quantità
di dati mancanti; meter nativo con nome accessibile, controlli da 44 px e layout
impilato su mobile. I testi lunghi delle fonti non disallineano prezzo e superficie.
Nessuna animazione decorativa aggiunta; disclosure e selettori usabili da tastiera.

Il filtro dei dati mancanti è condiviso da archivio, viste salvate ed export.
Include tutte le disponibilità quando aperto dalla pagina Qualità. La presenza
di un campo non attesta accuratezza. Il rilevamento dei duplicati rimane limitato
agli annunci caricati e dichiara il limite; le decisioni non cancellano le fonti.
Durante il salvataggio i comandi di revisione sono disabilitati.


## Fonti e importazione · formato, provenienza ed esito

| Before | After | Why |
|---|---|---|
| Importazioni e siti sotto lo stesso conteggio di fonti verificate | Cataloghi web e file importati in sezioni distinte | Un file caricato non prova l’accessibilità di un portale. |
| Schede import con metodo Locale ripetuto e test senza rete | Righe compatte con conteggi, apertura immobili e sospensione | Rende leggibili le azioni utili, conservando il controllo sulla fonte. |
| File selezionato e contenuto incollato con precedenza implicita | Scelta esplicita Carica file / Incolla testo | L’utente sa quale contenuto sta inviando; le due bozze restano conservate. |
| URL originale e due tracciati sempre visibili | URL richiesto solo per HTML e un tracciato per il formato corrente | Riduce i campi e i collegamenti irrilevanti. |
| Esito JSON | Nuovi, Aggiornati e Invariati; JSON in disclosure | L’esito serve a proseguire verso gli immobili o i benchmark. |
| Solo pulsante di invio disabilitato | Modulo e chiusura bloccati durante l’invio | Il contenuto non cambia mentre viene acquisito. |

Spazi di 12/20/24 px, header della finestra fisso, comandi da 44 px e campi mobile
da 16 px. I file importati non mostrano una disponibilità web né una percentuale
misurata quando mancano record. I titoli e i nomi lunghi vanno a capo; le azioni
restano separate. Nessuna nuova animazione decorativa o dipendenza UI.

Il formato scelto determina estensioni, tracciato e campi visibili. UTF-8 non valido,
contenuto vuoto e dimensione oltre 4 MB sono errori espliciti. Il server respinge
intestazioni vuote/duplicate e righe CSV con valori in eccesso prima di scrivere.
Gli errori preservano file e testo, riabilitano i controlli e ricevono il focus.
Un successo di importazione non viene trasformato in errore se fallisce il successivo
aggiornamento del workspace; l’esito acquisito resta visibile.

Il filtro della fonte resta visibile sopra l’archivio e può essere rimosso senza
aprire i filtri avanzati. Su schermi stretti il badge della fonte occupa una riga
propria, evitando di comprimere il nome. Gli stati vuoti usano una riga compatta.


## Benchmark e consultazione OMI

| Before | After | Why |
|---|---|---|
| Tabella lunga, limitata a 3.000 record caricati | Catalogo server con ricerca, stato, valuta e pagine da 20 | L’archivio resta raggiungibile senza caricarlo tutto nel browser. |
| Importi sempre in euro e senza decimali | Valuta originale, precisione fino ai centesimi e fonte apribile | Il formato non cambia il significato del dato. |
| Confrontabili contati sul campione caricato | Immobili con benchmark contati sull’intero archivio | Il limite di caricamento non determina la copertura dichiarata. |
| Metodo sempre visibile prima e dopo la tabella | Due indicatori, filtri, righe e metodo apribile | Le azioni e i dati restano in primo piano. |
| Zona OMI preselezionata e risultato precedente conservato cambiando destinazione | Zona esplicita, risultato invalidato a ogni cambio | Evita di leggere una fascia riferita a criteri diversi. |
| Vecchia richiesta capace di sostituire risultato o errore corrente | Guardie separate per elenco località e quotazioni | Le risposte superate e quelle a finestra chiusa non modificano l’interfaccia. |
| Tabella OMI larga su mobile | Schede con tipologia, fascia e base di superficie | Permette di leggere senza scorrimento orizzontale. |

Spazi di 12/16/20/24 px, controlli da 44 px, select mobile da 16 px. Le valute
restano esplicite una volta per fascia. Errori contestuali con Riprova; risultati
precedenti nascosti durante caricamento/errore, filtri in bozza conservati durante
il refresh e cancellati al logout. Nessuna animazione decorativa aggiunta.

La consultazione OMI non importa automaticamente un benchmark. La fascia mantiene
periodo, provenienza e base di superficie; una base assente non diventa Netta.
I documenti sintetici usati nel collaudo esistono solo nella cache temporanea QA.

## Confronto orientato alla decisione · 27 settembre 2026

| Before | After | Why |
|---|---|---|
| Una tabella fitta con tutti gli indicatori | Tre viste: Decisione, Mercato, Dati | Una domanda alla volta, senza eliminare informazioni. |
| Confronto costruito sul riepilogo del catalogo | Schede complete caricate per i 2–3 ID selezionati | Contatti, filiera, aggiornamento e quattro riferimenti restano coerenti con la scheda. |
| “Delta zona” e score ambiguo | Scostamento dal benchmark e priorità di verifica | Direzione e significato espliciti; nessuna implicazione di rendimento. |
| Disponibilità ignota descritta come non disponibile | “Da verificare” | Un dato mancante non equivale a un annuncio venduto. |
| Annunci dello stesso asset affiancati senza avviso | Avviso sui collegamenti confermati | Non contare fonti diverse come opportunità distinte. |
| Tabella orizzontale su mobile | Valori raggruppati per indicatore, con numero e comune | Contesto conservato a 320 px; tre annunci in righe separate. |
| Note metodologiche e domande sempre estese | Dettagli nativi apribili | Prezzo e contatto prima delle spiegazioni. |
| Export raggiungibile solo dall’archivio | Excel della selezione nel confronto | Esportare gli ID mostrati, anche se cambia la selezione esterna. |

Controlli da 44 px, spaziature 12/16/20/24 px, intestazioni ferme su desktop e
chiusura sempre raggiungibile. Tab accessibili con frecce/Home/End, nessuna nuova
animazione su azioni ripetute. Dati non convertiti tra valute; OMI con periodo,
fonte e base superficie. Campioni insufficienti e dati da ricontrollare espliciti.
Un errore su una scheda impedisce un confronto parziale; la selezione rimane
intatta e la risposta a finestra chiusa non la riapre. L’Excel riusa l’export
esistente e i dati correnti del database: non è una fotografia transazionale
della finestra. Nessun nuovo dato di mercato acquisito in questo intervento.

## Configurazione ricerche: bozze e salvataggio · 27 settembre 2026

| Before | After | Why |
|---|---|---|
| Chiudere elimina prompt e filtri non salvati | Bozza in memoria, recuperata riaprendo la stessa ricerca | Ridurre la perdita di lavoro senza presentare le modifiche come attive. |
| Editor costruito sull’ultimo elenco caricato | Configurazione letta dal server all’apertura | Valutare la bozza rispetto ai dati correnti disponibili. |
| Bozza vecchia applicata a una configurazione aggiornata | Ripresa esplicita o scarto, con campi bloccati fino alla scelta | Evitare sostituzioni silenziose della versione del team. |
| Campi modificabili durante l’invio | Fieldset e chiusura bloccati, stato Salvataggio | Identificare con precisione la configurazione inviata. |
| Recupero e configurazione attiva poco distinti | Bozza non salvata e Scarta bozza | Conservare controllo e chiarezza sullo stato. |
| Errore del refresh dopo un salvataggio confuso con errore di scrittura | Conferma della scrittura e richiesta di aggiornare l’elenco | Non suggerire una nuova creazione dopo una risposta positiva. |

Stato compatto sopra i criteri, spazi 12/16/20 px e controlli da 44 px. Niente
animazioni aggiunte: input e scelte ripetute devono rispondere subito. Il pulsante
Riprendi compare soltanto quando serve una scelta. Bozze isolate per utente e
ricerca (inclusa la nuova), cancellate al logout e dopo salvataggio confermato.
Un input riportato al valore originario rimuove la bozza. Fonti disabilitate e
motori non più disponibili non vengono riattivati dal recupero.

La memoria dura fino al ricaricamento/chiusura della pagina: il limite è indicato
nel modulo e il browser può avvertire prima di uscire. Nessun localStorage o invio
al modello per conservare una bozza. Non è un blocco concorrente sul server: una
modifica fatta da un altro operatore mentre l’editor è già aperto richiede ancora
coordinamento. Una perdita della risposta a una creazione POST non è resa idempotente
da questa funzione; il collaudo del retry interrompe la richiesta prima dell’invio.

## Salvataggi affidabili e conflitti · 27 settembre 2026

| Before | After | Why |
|---|---|---|
| Retry dopo una risposta persa può creare una seconda ricerca | Identificativo della richiesta conservato per il retry | Riconoscere una scrittura già ricevuta. |
| Una modifica aperta può sostituire quella di un collega | Revisione della configurazione controllata nella transazione | Preservare il lavoro del team. |
| Conflitto con Salva ancora principale | Rileggi ricerca in evidenza, Salva disabilitato | Rendere chiaro il prossimo passo. |
| Errore lungo senza azione | Messaggio breve, bozza conservata e rilettura esplicita | Risolvere senza ricompilare prompt e filtri. |
| Motore e frequenza affiancati, limite su una riga isolata | Tre colonne allineate su desktop, colonna singola su mobile | Raggruppare i controlli della stessa esecuzione. |

Recupero vicino al messaggio, target minimo di 44 px, nessuna animazione nuova.
Riprendere la bozza dopo la rilettura rimane una scelta esplicita. I dati del team
restano visibili prima della scelta; il sistema non tenta una fusione automatica.
Anche un successo HTTP con JSON troncato rimane un errore recuperabile.

Le ricevute server sono persistenti e contengono identificativo, autore, hash e
risposta, non una copia dei prompt. La chiave del browser resta nella sessione
pagina, come la bozza: ricaricare o uscire non conserva il retry. I vecchi client
API senza `request_id` o `expected_revision` restano compatibili e non ottengono
le rispettive protezioni. Lo scheduler non cambia la revisione di configurazione;
la pausa sì. Configurazione, screening collegato e ricevuta sono atomici.

## Oggi: coda completa e verifiche leggibili · 27 settembre 2026

| Before | After | Why |
|---|---|---|
| Il servizio elimina i risultati oltre 8 contatti e 4 verifiche | Restituisce tutti i candidati del campione esaminato | Nessun taglio invisibile nella shortlist. |
| Tutti i motivi concatenati in una riga | Motivo principale visibile, altri motivi e fonte apribili | Evidenza economica prima dei criteri ripetuti. |
| Contatto presente ma senza recapito utilizzabile | Recapito da trovare tra le verifiche | Non proporre una chiamata senza un canale valido. |
| Elenco completo potenzialmente lungo | Primi 8/4, gruppi aggiuntivi con conteggio e disclosure nativo | Sintesi iniziale e accesso agli altri candidati. |
| Aggiornare chiude i gruppi | Apertura conservata durante refresh e navigazione | Non perdere il contesto di lettura. |
| Link fonte con indirizzo assente | Azione presente solo con URL HTTP(S) | Nessuna navigazione inutile alla pagina corrente. |

Separazioni tra righe, spaziature esistenti da 20/24 px, riepiloghi apribili da
almeno 44 px e nessuna animazione aggiuntiva. Le verifiche sono avvisi, non errori
dell’app. Il numero dei contatti appartiene al campione: oltre 100 candidati il
limite resta esplicito e l’archivio è raggiungibile. Il backend mantiene priorità
dei richiami, esclusione dei chiusi, deduplicazione e verifiche di disponibilità.
Un recapito sintatticamente valido non certifica identità o mandato.

Gli aggiornamenti conservano anche i dettagli della provenienza e il focus sui
riepiloghi di Oggi. Il refresh visivo periodico attende mentre un controllo della
coda ha il focus; Aggiorna dati resta disponibile. Non cambia la programmazione
né l’esecuzione in background degli agenti. Una risposta già in corso può
aggiornare i dati, ripristinando apertura e focus sullo stesso elemento disponibile.

## Dati per decidere · feedback del cliente (settembre 2026)

Jacopo: arrivare prima al contatto giusto e capire se la piattaforma filtra meglio di un alert
del portale. Valentina: avere tutti i dati del suo metodo senza che l’AI decida al suo posto.

| Before | After | Why |
|---|---|---|
| Quattro riferimenti solo in fondo alla scheda, in quattro card | “Prezzo e mercato” subito sotto il prezzo: scala €/m² con richiesta, da ristrutturare, ristrutturato, nuovo, OMI e benchmark | Il metodo di Valentina in un colpo d’occhio; campioni e metodo restano apribili. |
| Anzianità, ribassi, catasto e cambio d’uso chiusi in “Catasto e storico” | Quattro fatti visibili sotto la scala; citazione del cambio d’uso | Sono i dati che lei usa per capire se l’annuncio ha senso. |
| Tabella con solo “Scarto benchmark” | “Vs mercato” (stesso stato, poi OMI, poi benchmark) e “Online da” con ribassi | Confronto omogeneo e urgenza del venditore già nell’elenco. |
| Età dall’inizio della raccolta presentata come età dell’annuncio | “≥” quando manca la data di pubblicazione | Un limite inferiore non viene spacciato per un dato. |
| Oggi senza numeri di mercato | Riga con delta, anzianità, ribassi e cambio d’uso; riepilogo “contatti pronti · da verificare · annunci monitorati” | Jacopo vede chi chiamare e perché, e la scala del lavoro filtrato. |
| Vista “Con ribassi” assente | Vista rapida e ordinamento “Da più tempo online” | Trova venditori motivati senza filtri manuali. |
| Varianti di una ricerca da ricreare a mano | “Duplica” sulla ricerca | Valentina crea varianti in autonomia. |
| Strategie e tipologie nascoste in “Filtri avanzati” | Visibili nei criteri; avanzati solo superficie massima e aste | Value add, core plus, development sono il primo filtro, non un dettaglio. |
| Excel con i riferimenti lontani dai delta, stati in inglese, date ISO | Selezione ordinata come la scheda: prezzo, 4 riferimenti con Δ, anzianità, dichiarazioni, contatto; etichette italiane e date Excel | Lavoro su più immobili in parallelo, stessi numeri della piattaforma. |
| 220 regole con testo a 7–10 px | Minimo 11 px | Leggibile su qualsiasi schermo. |
| Due campi di ricerca identici in Immobili; filtri prima dei risultati su mobile | Una ricerca; filtri dietro un pulsante con contatore sul telefono | Risultati al primo scroll. |

Nessuna nuova dipendenza. La scheda entra dal lato destro (260 ms, curva drawer), i
separatori non restano a inizio riga, `prefers-reduced-motion` resta rispettato.
