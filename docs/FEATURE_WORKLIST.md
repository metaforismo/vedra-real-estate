# Flusso locale: dalla ricerca alla shortlist

- [x] Istruzioni qualitative per agente, salvate e trasmesse a Hermes/AI.
- [x] Esito documentato: coerente, non coerente, da verificare; prompt e contenuto aggiornati invalidano risultati precedenti.
- [x] Filtri numerici e benchmark restano vincoli deterministici, separati dall'interpretazione AI.
- [x] Excel principale: selezione, scheda singola, riepilogo operativo, evidenze e riferimenti con dati mancanti espliciti.
- [x] Scheda e ricerca mostrano ragioni dello screening e criteri personalizzati.
- [x] Quattro riferimenti economici distinti: da ristrutturare, ristrutturato, nuovo e OMI; campioni e fonti verificabili, nessun valore sintetico.
- [x] Home Oggi: recapiti acquisiti, motivo della selezione, richiami e contatti mancanti; quattro voci principali, funzioni avanzate conservate.
- [x] Istruzioni di ricerca distinte dai criteri di selezione; pagine specifiche sul dominio di fonti collegate, configurazione congelata per esecuzione e traccia delle visite.
- [x] Verifica AI di ogni requisito su una riga: citazioni, esito e dati mancanti; un requisito ignorato non può produrre una corrispondenza completa.
- [x] Dichiarazioni catastali, cambio d’uso, mandato e pubblicazione; separazione da verifiche del team, prima rilevazione e ribassi omogenei osservati.
- [x] Registro contatti con esito, nota, richiamo, autore e verifica umana del mandato; retry idempotenti e permessi di scrittura.
- [x] Excel con recapiti, riferimenti, criteri riga per riga e foglio Contatti.
- [x] Dossier dello stesso asset: collegamenti confermati dal team, prezzi, recapiti, disponibilità e divergenze per fonte.
- [x] Coda Oggi senza doppie chiamate sullo stesso asset confermato; richiamo condiviso tra annunci collegati e verifica preventiva per disponibilità discordante.
- [x] Campioni con numero fonti, date, quartili e avvisi su concentrazione e dispersione. Asset discordanti esclusi dalle statistiche.
- [x] Fasce OMI visibili nei quattro riferimenti; metodo e benchmark apribili, senza perdere funzioni.
- [x] Excel a dieci fogli con confronto tra fonti e storico coerente per valuta e operazione.
- [x] Collaudo API, isolamento dei criteri fra ricerche, modifica prompt, Excel, browser desktop/mobile e stati vuoti.

- [x] Qualità sull’intero archivio: filtro per campo mancante, viste salvate ed export coerenti; duplicati con confronto delle fonti e decisioni reversibili.

- [x] Fonti web distinte dai file; importazione con formato e input espliciti, validazione CSV/UTF-8, riepilogo leggibile e accesso ai dati importati.

- [x] Catalogo benchmark paginato e filtrabile, valute e fonti preservate; consultazione OMI con selezione esplicita, risposte superate ignorate e riprova.

- [x] Confronto di 2–3 schede complete: contatti e verifiche, quattro riferimenti, catasto e storico; valute esplicite, avviso stesso asset, Excel della selezione e navigazione da tastiera.

- [x] Bozze dei criteri recuperabili nella sessione della pagina, isolate per ricerca e utente; configurazione riletta all’apertura, scelta esplicita se cambiata, salvataggio con campi bloccati e stato chiaro.

Solo sviluppo e verifica locali. Nessun deploy o modifica al workspace remoto.

## Uso

1. Configura una ricerca: budget, zona, superficie, strategie e sconto minimo sul benchmark.
2. Scrivi un requisito di selezione per riga e seleziona Hermes o AI verticale. Per guidare le visite, apri “Istruzioni per Hermes”, aggiungi istruzioni di ricerca e una pagina per fonte, quindi abilita Hermes online. Il motore a regole non interpreta un prompt.
3. Esegui la ricerca. Gli esiti incerti rimangono fuori dai criteri; nella scheda trovi motivazione e citazioni.
4. In Oggi trovi i candidati pubblicati e selezionati, con recapiti o una verifica da completare. Registra contatto, esito e prossimo richiamo.
5. Seleziona gli asset e scarica Excel. Word rimane disponibile nella scheda.

I tre campioni di annunci confrontano prezzi richiesti: stessa zona dichiarata, tipologia, base superficie, valuta, compravendita e superficie entro ±30%, osservati negli ultimi 90 giorni. Mediane da almeno tre asset; OMI resta separato. Lo sconto minimo usa soltanto il benchmark compatibile, non le mediane né scenari OMI condizionati. Nessuna stima automatica del margine.

I criteri si applicano al testo acquisito e alle dichiarazioni del broker collegate all’annuncio. Le istruzioni di ricerca sono trasmesse a Hermes con il perimetro e i link consentiti; le visite vengono registrate, senza certificare automaticamente che ogni istruzione libera sia stata eseguita. Non abilita nuovi siti, contatti o strumenti e non verifica un mandato, una destinazione catastale o un cambio d’uso presso gli enti. I risultati precedenti non valgono per un prompt o una versione dell’annuncio diversi.

Le nuove risposte AI sono verificate con contratti e fixture locali: il collaudo non attesta una nuova esecuzione del modello sulla VPS. Nessun deploy effettuato.

## Limiti da validare sul campo

- Le risposte del modello di questi collaudi sono fixture: accuratezza su nuove ricerche Hermes da misurare separatamente.
- I recapiti automatici richiedono dati strutturati associati all’annuncio. Un numero nel footer del sito non viene attribuito al bene; il mandato resta da verificare.
- Quotazioni e comparabili dipendono dai dati disponibili e dalla loro compatibilità. Nessuna promessa di valore di rivendita o margine.
- La coda Oggi mostra al massimo 8 contatti e 4 verifiche sui primi 100 candidati idonei; i richiami scaduti hanno precedenza. L’archivio resta completo.
- Un esito “raggiunto” o “documenti richiesti” senza richiamo esce dalla coda; un richiamo futuro ricompare alla data stabilita. Lo storico conserva gli esiti.
- Copertura dei portali, nuovi recapiti reali, calibrazione delle soglie e tempi risparmiati richiedono un pilota con fonti accessibili e valutazioni del team.

## Evidenze incrociate

I collegamenti tra annunci derivano dalle revisioni del team nella sezione Qualità:
non basta un indirizzo simile per dichiarare due annunci uguali. Il dossier conserva
prezzi, superfici, stato e recapiti di ogni fonte e mostra le divergenze. Un conflitto
sulla disponibilità o sull’identità sposta il candidato fra le verifiche di Oggi.
I richiami e gli esiti già gestiti valgono per il gruppo confermato; non vengono
replicati come nuove telefonate. Il registro originario conserva l’annuncio contattato.

Nei comparabili ogni asset confermato conta una volta. Gruppi con dati discordanti
o incompleti per il limite di visualizzazione sono esclusi dal campione. I quartili
descrivono il 50% centrale dei prezzi richiesti; non misurano la precisione di una
stima. Una sola fonte o una dispersione superiore al 50% della mediana produce un
avviso. Lo scarto richiesta/mediana si mostra soltanto per lo stesso stato manutentivo.

La scheda mostra al massimo 100 annunci per gruppo e segnala il confronto parziale;
questi gruppi richiedono verifica. Le statistiche restano limitate ai 1.000 annunci
compatibili più recenti e il dettaglio ai primi 12 asset per categoria, con avviso.
Le fonti contate per dominio possono condividere lo stesso annuncio: il numero non
certifica indipendenza. Queste funzioni aggregano dati disponibili; non aggiungono
nuove acquisizioni di mercato o quotazioni sintetiche.


## Opportunità, filiera e scenari

- [x] Nuove ricerche UI con “Solo sotto benchmark” preselezionato: prezzi in linea,
  sopra benchmark o privi di confronto restano fuori. Sconto minimo configurabile;
  ricerche esistenti preservate e opzione disattivabile.
- [x] Filiera configurabile: qualsiasi inserzionista, precedenza al diretto o solo
  diretto dichiarato con recapito. La dichiarazione richiede frasi esplicite nella
  pagina acquisita; no agenzie, logo, nome e numero non bastano. Negazioni, richieste
  di incarichi e dichiarazioni contraddittorie restano da verificare.
- [x] Brief e istruzioni Hermes includono contatto cercato e vincoli economici; ricerca
  della pubblicazione originaria limitata alle fonti consentite. Nessun invio di messaggi.
- [x] Oggi privilegia il recapito diretto dichiarato anche fra annunci dello stesso
  asset, conservando priorità dei richiami e conflitti da verificare.
- [x] Scenario in piattaforma: ROI obiettivo, massimo prezzo d’acquisto, stress
  simultaneo su rivendita, lavori e durata. Le ipotesi sono modificabili e salvabili.
- [x] Excel esporta gli stessi scenari salvati e risultati del calcolatore condiviso,
  oltre alla filiera con citazione. Nessuna funzione analitica riservata all’export.
- [x] Modificare le ipotesi invalida il risultato; risposte tardive e caricamento di
  uno scenario precedente non ripristinano calcoli estranei ai valori correnti.

Il tetto d’acquisto deriva da ricavo netto / (1 + ROI obiettivo) meno i costi diversi
 dall’acquisto. È arrotondato per difetto ai centesimi. Costi di acquisto e imposte
inserite rimangono fissi: vanno rivisti se cambia il prezzo. Capitale senza debito,
ROI non annualizzato; imposte o costi non inseriti restano esclusi. Un tetto negativo
non viene trasformato in zero: nessun prezzo positivo soddisfa quelle ipotesi.

Le ipotesi di stress iniziali (ribasso 10%, lavori +20%, ritardo 6 mesi) sono parametri
editabili, non statistiche di mercato. Il foglio Scenari è un’istantanea dei calcoli
salvati, non un modello Excel autonomo. Nessuna Monte Carlo né probabilità di guadagno:
non sono disponibili distribuzioni e correlazioni calibrate. Sconto su benchmark e
margine nello scenario sono concetti distinti; nessuno certifica un investimento.

## Prima del contatto

- [x] Dati oltre la frequenza di ricontrollo della fonte (24 ore predefinite) tra le
  verifiche di Oggi; data assente, non valida o futura non considerata recente.
- [x] Distinzione fra pagina acquisita e importazione. Non modifica disponibilità o
  storico e non dichiara un immobile venduto per la sola scadenza.
- [x] Ultimo contatto su un annuncio collegato visibile con accesso al record originale;
  verifica del mandato non trasferita automaticamente a un altro intermediario.
- [x] Domande derivate da disponibilità, mandato, catasto, cambio d’uso, prezzi discordanti,
  anzianità e riferimenti mancanti. Apribili nella scheda ed esportate in Excel.

Vedi [revisione dei requisiti](REQUIREMENTS_REVIEW.md) per distinguere funzioni locali
e aspetti che richiedono ancora dati reali, documenti o un pilota operativo.

## Leggere l’esito di una ricerca

- [x] Esito e conteggi di acquisizione prima del registro tecnico.
- [x] Analisi richieste, risposte accettate e task ancora mancanti per esecuzione.
- [x] Brief e pagine di partenza/visitate separati, dalla configurazione salvata all’avvio.
- [x] Esito per criterio e citazioni apribili, senza ripetere prompt ed evidenze.
- [x] Pannelli e focus conservati negli aggiornamenti live; collegamento ai risultati attuali.

“Accettata” significa risposta conforme al contratto: può essere negativa o incerta.
Il contatore non certifica accuratezza, pertinenza degli investimenti o lettura di
ogni istruzione libera. Zero nuovi task può anche significare riuso di analisi
già disponibili; non equivale a una nuova esecuzione del modello.

## Storico prima della decisione

- [x] Anteprima breve con valuta originale di ogni rilevazione, senza usare quella attuale come fallback.
- [x] Prezzo, disponibilità, superficie e descrizione in primo piano; altri campi apribili.
- [x] Testi storici integrali consultabili; dettagli tecnici e metodo separati.
- [x] Caricamento progressivo con recupero dagli errori e ritorno alla scheda immobile.
- [x] Variazione percentuale osservata con contesto invariato, condivisa con l'Excel.

I ribassi osservati descrivono cambiamenti nei prezzi richiesti: non certificano
uno sconto sul mercato. L'assenza di storico resta esplicita.

## Salvataggi delle ricerche

- [x] Retry di creazione/modifica riconosciuti tramite ricevuta persistente.
- [x] Revisione server per evitare che un editor aperto sovrascriva un collega.
- [x] Conflitto con bozza conservata, rilettura e ripresa/scarto espliciti.
- [x] Configurazione e screening degli annunci collegati nella stessa transazione.
- [x] Recupero leggibile su desktop/mobile, azione principale coerente con lo stato.

Il frontend invia entrambi i campi di protezione. La compatibilità dei vecchi
client API non impone loro questi campi. Bozza e chiave di retry del browser
restano limitate alla pagina corrente; non sono backup persistenti.

## Coda di contatto completa

- [x] Tutti i candidati esaminati raggiungibili in Oggi, oltre i precedenti 8/4.
- [x] Conteggi coerenti e limite dei 100 candidati esplicito.
- [x] Recapiti assenti/non validi tra le verifiche, con motivo leggibile.
- [x] Gruppi aggiuntivi apribili da tastiera e stato conservato al refresh.
- [x] Scostamento dal benchmark visibile; criteri ripetuti e fonte nei dettagli.

Il conteggio non rappresenta l’intero mercato e un contatto pronto non certifica
la convenienza economica: restano validi criteri, evidenze e revisione del team.
