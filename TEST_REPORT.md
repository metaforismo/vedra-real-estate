# Verifiche Vedra 0.4.0

## Aggiornamento locale · coda completa di Oggi · 27 settembre 2026

- Corretto un taglio silenzioso: il servizio restituiva solo 8 contatti e 4 verifiche anche quando aveva esaminato altri candidati. Ora restituisce l’intero campione elaborato (massimo 100 candidati iniziali); il frontend mantiene 8/4 in apertura e rende gli altri raggiungibili tramite gruppi con conteggio. Limite del campione e accesso all’archivio restano espliciti.
- Recapiti assenti, malformati o con tipo inatteso non rendono un candidato contattabile. Il motivo Recapito da trovare compare tra le verifiche; un recapito sintatticamente valido non verifica identità, mandato o convenienza. Deduplicazione, disponibilità e richiami mantengono le regole precedenti.
- Motivo principale visibile (scostamento dal benchmark quando disponibile), criteri ulteriori e provenienza apribili. Link fonte assente se l’indirizzo non è utilizzabile. Avvisi distinti dagli errori, righe separate e titoli lunghi contenuti.
- **62 flussi browser passati, zero errori JavaScript**, su Chrome, backend HTTP e database temporanei isolati, senza relay o sessione operativa. Fixture finale: 12 contatti e 6 verifiche tutti raggiungibili; espansione da tastiera, refresh, apertura dell’ultimo immobile e chiusura della sezione verifiche. Schermate a 320/393/768/1440 px, target disclosure >=44 px e nessun overflow. Desktop e mobile ispezionati visivamente.
- Test di risposta ritardata: durante il refresh si apre la provenienza e si mantiene il focus; alla sostituzione della pagina, dettaglio aperto e focus sono ripristinati. Il refresh visivo automatico attende mentre un controllo di Oggi ha il focus; non modifica l’esecuzione degli agenti. Il ramo periodico è verificato nel codice, il ripristino con HTTP ritardato nel browser.
- I primi collaudi hanno segnalato un selettore QA troppo ampio e un controllo eseguito prima della fine del refresh. Selettore ristretto al riepilogo diretto e attesa della sostituzione del pannello; riesecuzione completa passata. Aggiunta la conservazione della provenienza e del focus, prima mancanti.
- **520 test Python passati, 6 skip**, warning Starlette/AnyIO preesistente. Cinque integrazioni PostgreSQL richiedono TEST_DATABASE_URL usa-e-getta; un connettore richiede BROWSER_TEST_EXECUTABLE. **92 test JavaScript**, **33 moduli JS**, **8 invarianti mappa**, **7 verifiche worker/API**, compilazione Python e diff-check passati.
- Artefatti: `artifacts/ui-today-complete/report.json`, `today-complete-320.png`, `today-complete-393.png`, `today-complete-768.png`, `today-complete-1440.png`. Solo fixture QA; nessuna nuova acquisizione di annunci, quotazione corrente, chiamata Hermes remota, deploy o push verificati.

## Aggiornamento locale · salvataggi e conflitti delle ricerche · 27 settembre 2026

- **61 flussi browser passati, zero errori JavaScript**, su HTTP/backend/database/Chrome temporanei isolati; nessun relay o accesso alla sessione operativa. Artefatti: `artifacts/ui-research-save/report.json`.
- Creazione realmente ricevuta e salvata dal backend, risposta al browser interrotta, retry con lo stesso ID e una sola ricerca nel database. Il precedente caso di interruzione prima dell’invio resta coperto.
- Modifica concorrente: l’editor propone 630.000, il database viene aggiornato a 640.000; il server rifiuta la versione vecchia. La bozza resta 630.000 e il database 640.000 fino a rilettura, scelta esplicita e nuovo salvataggio.
- Recupero a 320, 393, 768 e 1440 px: messaggio breve, Rileggi ricerca principale, Salva disabilitato dopo un conflitto, nessun overflow e comando di recupero da almeno 44 px. Schermate finali desktop/mobile ispezionate; motore/frequenza/limite allineati su desktop.
- Ricevute persistenti per utente e payload; stesso identificativo con contenuto diverso rifiutato, replay successivo a un’ulteriore modifica non riscrive dati vecchi. Concorrenza SQLite con un solo vincitore, rollback di configurazione/ricevuta se fallisce lo screening, pause incluse e timestamp scheduler esclusi dalla revisione. Validazione delle fonti nella stessa connessione della transazione, senza occupare una seconda connessione del pool.
- **517 test Python passati, 6 skip**: cinque integrazioni PostgreSQL senza TEST_DATABASE_URL e un connettore senza BROWSER_TEST_EXECUTABLE. Warning Starlette/AnyIO preesistente. La suite ha inizialmente segnalato un’aspettativa obsoleta di sei migrazioni; aggiornata alla nuova migrazione additiva 7, riesecuzione completa passata.
- **90 test JavaScript**, **33 moduli sintatticamente validi**, **8 invarianti mappa**, **7 verifiche API/worker**, compilazione Python e diff-check passati. Il client rifiuta anche un JSON troncato su HTTP di successo: questo ramo è coperto dal test unitario, non dalla simulazione browser di rete.
- Queste protezioni completano i limiti concorrenti descritti nel precedente aggiornamento: il frontend invia `request_id` e `expected_revision`. I client API precedenti possono ancora ometterli. Bozza e chiave di retry del browser durano fino al ricaricamento/logout; le ricevute server persistono. Nessuna garanzia di deduplicazione dopo perdita della chiave client.
- Solo fixture QA locali: nessuna nuova acquisizione immobiliare, chiamata Hermes remota, aggiornamento OMI, deploy o push verificato in questo intervento.

## Aggiornamento locale · bozze delle ricerche · 27 settembre 2026

- **59 flussi browser passati, zero errori JavaScript**, con HTTP, backend, database e Chrome temporanei isolati. Nessun relay né sessione operativa.
- Prompt, istruzioni di visita, filtri e fonti recuperabili riaprendo la ricerca nella stessa pagina. Nessun invio o salvataggio sul server finché l’utente non salva. Stato della bozza esplicito, azione Scarta bozza e avviso del browser prima del ricaricamento (verificata la cancellabilità dell’evento, non la finestra nativa).
- Bozze in memoria, isolate per utente e ricerca, nessun localStorage. Logout e salvataggio confermato le cancellano; riportare gli input ai valori iniziali elimina la bozza. Isolamento, reset e ruoli in sola lettura coperti dai test JS.
- L’editor rilegge gli agenti dal server all’apertura. Una configurazione diversa dalla base della bozza richiede una scelta esplicita: Riprendi bozza o Scarta bozza. Il browser verifica che 610.000 di una bozza non sostituisca automaticamente 620.000 impostato nel database QA. Fonti disabilitate e motori non più disponibili non vengono riattivati dal ripristino.
- Durante il salvataggio campi, comandi e chiusura sono bloccati. Il test interrompe una richiesta prima dell’invio: i valori restano, il retry funziona e il successo rimuove la bozza. Un errore di refresh successivo alla scrittura ha ora un messaggio distinto dal fallimento del salvataggio; questo ramo è stato revisionato nel codice.
- Schermate a 320, 393, 768 e 1440 px; barre di stato e conflitto ispezionate visivamente, nessun overflow orizzontale. Chiusura da 44 px, Riprendi nascosto quando non pertinente. L’ultima riduzione del testo durante Salvataggio è coperta dal test JS; gli screenshot precedono solo questa rimozione del suggerimento ridondante.
- Il primo run ha evidenziato la lettura di una configurazione vecchia dall’elenco; corretta caricando i dati all’apertura. L’ispezione visiva ha evidenziato lo stile `.btn` che rendeva visibile un pulsante `hidden`; aggiunta la regola locale e verifica browser dell’assenza del comando.
- **509 test Python passati, 5 skip**, warning Starlette/AnyIO. Quattro test PostgreSQL richiedono TEST_DATABASE_URL usa-e-getta; un test del connettore richiede BROWSER_TEST_EXECUTABLE. **85 test JavaScript**, **33 moduli JS**, **8 invarianti mappa**, **7 controlli API/worker**, compilazione Python e diff-check passati.
- Limiti: la bozza dura fino al ricaricamento o logout; non è un salvataggio persistente. La verifica all’apertura non sostituisce un controllo concorrente server-side durante tutta la modifica. Nessuna garanzia di idempotenza per una creazione POST la cui risposta venga persa dopo l’inserimento: il test di rete qui interrompe prima della scrittura.
- Artefatti: `artifacts/ui-research-drafts/report.json`, `research-draft-*.png`, `research-saving.png`. Solo fixture locali. Nessuna nuova acquisizione, esecuzione Hermes remota, commit, push o deploy.


## Aggiornamento locale · confronto decisionale · 27 settembre 2026

- **56 flussi browser passati, zero errori JavaScript**. Backend HTTP, database e profilo Chrome temporanei; nessun relay o accesso alla sessione operativa.
- Confronto di 2–3 immobili dalle API delle schede complete, anziché dai riepiloghi del catalogo. Sezioni Decisione, Mercato e Dati con contatti, filiera, aggiornamento, quattro riferimenti, catasto, pubblicazione, ribassi e provenienza. Gli indicatori precedenti sono conservati, con etichette esplicite.
- Desktop con colonne allineate e intestazioni ferme; mobile raggruppato per indicatore. Verificati 320, 393, 768 e 1440 px, chiusura da 44 px, testi lunghi, tre annunci, tab con frecce/Home e dettagli da tastiera. Domande e metodo apribili. Schermate finali ispezionate.
- Valute e decimali preservati. Disponibilità ignota resa come “Da verificare”; score e dati assenti non trasformati in zero. OMI scaduto escluso dai valori correnti; periodo, superficie, fonte e data mantenuti. Avviso per valute/operazioni diverse e annunci collegati allo stesso asset.
- Una scheda fallita impedisce di mostrare un confronto parziale; riprovare conserva la selezione. Chiudere durante il caricamento impedisce a una risposta tardiva di riaprire la finestra. Excel verificato con openpyxl: esattamente gli ID del confronto. L’export legge i dati correnti del database, non una fotografia transazionale della finestra.
- Il caso popolato usa fixture QA: tre asset/tre fonti per categoria, fasce OMI sintetiche già memorizzate, contatti e collegamenti confermati nel database temporaneo. Nessuna acquisizione di nuovi annunci, quotazioni live o verifica remota Hermes in questo intervento.
- **509 test Python passati, 5 skip**, un warning di deprecazione Starlette/AnyIO. Quattro skip PostgreSQL senza TEST_DATABASE_URL usa-e-getta; uno del connettore browser senza BROWSER_TEST_EXECUTABLE. Il browser UI separato usa Chrome esplicitamente.
- **78 test JavaScript passati**, inclusi otto nuovi casi sul confronto. **32 moduli JS**, **8 invarianti mappa**, **7 verifiche API/worker**, compilazione Python e `git diff --check` passati.
- Artefatti locali: `artifacts/ui-comparison-polish/report.json`, `comparison-*.png`, `comparison.xlsx`. Nessun commit, push o deploy.


## Aggiornamento locale · benchmark e consultazione OMI · 27 settembre 2026

- **53 flussi browser passati, zero errori JavaScript**, in backend HTTP, database e profilo Chrome temporanei separati. Nessun relay o accesso alla scheda operativa.
- Catalogo benchmark con ricerca per comune/zona/fonte, stato immobile, valuta e pagine server da 20 righe. Un test con **3.002 riferimenti** trova un record oltre il vecchio limite di caricamento di 3.000. Ordinamento stabile, valori di ricerca letterali, record dimostrativi esclusi e query non valide rifiutate. La vecchia API resta compatibile; il frontend usa il nuovo catalogo.
- Valuta originale, importi fino a due decimali, tipologia, stato, base superficie, operazione, semestre e fonte consultabile. Copertura degli immobili ricavata dai conteggi dell’intero archivio. Metodo apribile; righe adattive su mobile. Verificata la conservazione del testo ancora da cercare durante l’aggiornamento generale; reset dei dati e della bozza al logout coperto da test JS.
- OMI: provincia/comune/zona espliciti, risultato invalidato cambiando zona o destinazione, guardie separate per metadati e quotazioni, errori con Riprova. Risposte superate non cambiano risultato, errore o pulsante della richiesta corrente; quelle a finestra chiusa sono ignorate. Base di superficie mancante non presentata come Netta; link non navigabili restano testo.
- Prove OMI eseguite tramite l’API e il parser effettivi su **documenti sintetici nella cache QA temporanea**, non su nuove quotazioni live. Nel browser una richiesta per B1/Residenziale viene superata da D1/Commerciale; compare solo il risultato corrente. Testata anche la riprova dopo errore HTTP e un successivo cambio a Terziaria. Test JS separati ignorano l’abort per verificare le risposte tardive.
- Benchmark e risultati OMI verificati a **320, 393, 768 e 1440 px** senza overflow orizzontale del documento. Filtri mobile su righe complete, comandi da 44 px, intestazione della finestra fissa e fasce OMI leggibili senza tabella orizzontale. Ispezionate le schermate finali.
- **509 test Python passati, 5 skip**, un warning Starlette/AnyIO. Esclusi quattro test PostgreSQL senza database usa-e-getta e uno del connettore browser senza eseguibile configurato. **70 test JavaScript**, **31 moduli JS**, **8 controlli mappa**, **7 verifiche API/worker**, compilazione Python e diff-check passati.
- Il primo collaudo usava un selettore Cerca ambiguo con quello della navigazione globale: ristretto al modulo benchmark. Controllo visivo seguito da correzione dei filtri compressi a 320 px, singolare “1 riferimento” e decimali delle fasce. Suite browser rieseguita dopo le rifiniture.
- Riscontri locali ignorati da Git: `artifacts/ui-market-polish/`, con report JSON, screenshot desktop/mobile ed export dei percorsi di regressione.
- **Limite:** nessuna nuova acquisizione di mercato, verifica live di OMI/Hermes o deploy. Il collaudo attesta il comportamento sui casi QA; non certifica quotazioni correnti o precisione delle stime.


## Aggiornamento locale · fonti e importazioni · 27 settembre 2026

- **51 flussi browser passati, zero errori JavaScript**, con backend HTTP, database e profilo Chrome temporanei. Nessun relay o accesso alla scheda operativa.
- Fonti: cataloghi web separati dai file importati; rimossi i test di rete senza effetto sulle fonti locali. File in righe compatte, apertura degli immobili e sospensione conservate. Qualità non misurata indicata con un trattino; nessuna importazione descritta come accesso web verificato. Filtro fonte visibile e rimovibile nell’archivio.
- Importazione: scelta esplicita file/testo, formato e tracciato coerenti, URL richiesto solo per HTML. Errori per contenuto vuoto, formato errato, UTF-8 non valido e oltre 4 MB. File e testo restano conservati dopo gli errori. Modulo e chiusura bloccati durante l’invio; focus sull’errore dopo il rifiuto.
- Esito con Nuovi, Aggiornati e Invariati, dettagli tecnici apribili e accesso diretto agli immobili importati o ai benchmark. Verificata una risposta HTTP persa dopo la scrittura: il reinvio conserva **tre immobili**, con **zero nuovi e tre invariati**.
- CSV: rifiuto di intestazioni duplicate/vuote, valori oltre le colonne dichiarate e virgolette non valide prima della scrittura. Conservato supporto per BOM, separatori virgola/punto e virgola/tab e valori quotati multilinea. Header con spazi esterni normalizzati.
- Modulo, esito, elenco fonti e fonte bloccata verificati a **320, 393, 768 e 1440 px**, senza overflow orizzontale. Comandi da 44 px, header della finestra fisso, errori apribili da tastiera e badge mobile separato dal nome. Verificate sospensione e riabilitazione della fonte nel database QA. Controllate visivamente le schermate finali.
- **505 test Python passati, 5 skip**, un warning Starlette/AnyIO. Skip: quattro test PostgreSQL senza database usa-e-getta e uno del connettore browser senza eseguibile configurato. **61 test JavaScript**, **28 moduli JS**, **8 controlli mappa**, **7 verifiche API/worker**, compilazione Python e diff-check passati.
- Il primo collaudo ha individuato il nome accessibile instabile del selettore del formato: corretto. L’intercettazione del test ora attende l’invio HTTP dopo la lettura asincrona del file. Il controllo visivo ha portato a ridurre gli spazi duplicati del modulo e a spostare il badge sotto il titolo su mobile. Suite browser completa rieseguita dopo i ritocchi.
- Riscontri locali ignorati da Git: `artifacts/ui-import-polish/`, con report JSON, screenshot ed export dei flussi di regressione.
- **Limite:** fixture e processi QA isolati; nessuna nuova acquisizione di mercato, verifica live remota di Hermes o deploy. Il precedente blocco del plugin Browser sulla scheda operativa resta rispettato.


## Aggiornamento locale · qualità dei dati e duplicati · 27 settembre 2026

- **49 flussi browser passati, zero errori JavaScript**, con backend HTTP, database e profilo Chrome temporanei separati. Nessun relay o accesso alla scheda operativa.
- Copertura dei dieci campi e annunci senza benchmark calcolati sull’intero archivio, incluse le disponibilità archiviate. Regressione con **2.006 record**: i conteggi restano completi oltre il limite di 2.000 annunci caricati. Archivio vuoto senza percentuale artificiale.
- Ogni campo mancante apre gli annunci pertinenti. Il vincolo resta visibile fuori dai filtri avanzati, può essere rimosso e si conserva nelle viste salvate e negli export. Test API su tutti i dieci campi e valori invalidi; Excel scaricato dal browser e riaperto con lo stesso numero di risultati, compreso un annuncio venduto senza prezzo.
- Duplicati: fonti affiancate, prezzi allineati anche con titoli di diversa lunghezza, ragione apribile, separazione fra Da verificare e Già valutati. Verificati blocco dei comandi durante il salvataggio, persistenza e modifica della decisione da Stesso asset ad Annunci distinti. Permessi di sola lettura coperti nei test JS. Il confronto resta limitato agli annunci caricati: limite esplicito in UI.
- Schermate a **320, 393, 768 e 1440 px**, senza overflow orizzontale del documento. Controlli da almeno 44 px, disclosure da tastiera, focus recuperato sui selettori e fonti impilate su mobile. Ispezionate le schermate desktop e mobile, con ulteriori acquisizioni viewport per evitare artefatti di composizione degli screenshot a pagina intera.
- **498 test Python passati, 5 skip**, un warning Starlette/AnyIO. Esclusi quattro test PostgreSQL senza database usa-e-getta e uno del connettore browser senza eseguibile configurato. **54 test JS**, **26 moduli JS**, **8 controlli mappa**, **7 verifiche processi API/worker**, compilazione Python e diff-check passati.
- Durante il collaudo corretti due dettagli del test: attesa del badge di decisione salvata anziché del testo già presente sul pulsante, e conteggio mobile aggiornato per i due nuovi annunci pubblicati della fixture QA. Corretta anche la label singolare “1 mancante”. Suite browser completa rieseguita fino agli scenari e agli export finali.
- Riscontri locali ignorati da Git: `artifacts/ui-quality-polish/`, inclusi report JSON, screenshot e `missing-prices.xlsx`.
- **Limite:** prove con fixture QA e servizi locali; nessun nuovo dato di mercato acquisito, esecuzione remota Hermes o deploy. I controlli attestano il comportamento dell’applicazione nei casi verificati, non l’accuratezza del mercato live.




## Aggiornamento locale · cronologia degli annunci · 27 settembre 2026

- **47 flussi browser passati, zero errori JavaScript**, con backend HTTP, database e profilo Chrome temporanei separati. Nessun relay o accesso alla scheda operativa.
- Scheda immobile: anteprima delle ultime tre rilevazioni, prezzo con valuta originale e accesso a tutta la cronologia. Valuta storica mancante non sostituita con quella attuale. Importi con centesimi; nessun prezzo mancante trasformato in zero.
- Cronologia: titolo dell'immobile, ritorno alla scheda, confronto Prima/Dopo, campi principali in evidenza e secondari apribili. Descrizioni integrali conservate, senza il precedente taglio a 600 caratteri. Parser e metodo consultabili separatamente. Disponibilità ignota mostrata come Da verificare, campo assente come Non registrata.
- API: snapshot sintetico tratto dai campi originali e variazione percentuale condivisa con Excel. Il calcolo richiede prezzi/superfici positivi, valuta nota e contesto invariato; cambi di valuta, contratto, superficie o base interrompono il confronto. Nessuna ricostruzione dalle informazioni attuali.
- **36 rilevazioni QA**: prime 30 più caricamento progressivo, conservazione dei pannelli aperti, riprova dopo errore HTTP e risposta in ritardo ignorata dopo la chiusura. File Excel scaricato dal browser e riaperto: tutte le 36 righe presenti, variazione della rilevazione controllata **−1,5%**, identica al calcolo condiviso. Test API separato sulla parità cronologia/Excel a **−5%**.
- Schermate a **320, 393, 768 e 1440 px**, senza overflow orizzontale del documento. Intestazione fissa, chiusura da 44 px, Prima/Dopo impilati su mobile e disclosure utilizzabili da tastiera. Controllate visivamente le viste desktop/mobile finali.
- **495 test Python passati, 5 skip**, un warning Starlette/AnyIO. Esclusi quattro test PostgreSQL senza database usa-e-getta e uno del connettore browser senza eseguibile configurato. **49 test JS**, **25 moduli JS**, **8 controlli mappa**, **7 verifiche processi API/worker**, compilazione Python e diff-check passati.
- La prima esecuzione UI ha rilevato un metadato obbligatorio mancante nella nuova fixture storica: fixture corretta. Il controllo visivo ha poi trovato la label availability non tradotta: corretta e coperta da test. Suite browser completa rieseguita sul risultato finale.
- Riscontri ignorati da Git: `artifacts/ui-history-polish/`, con report JSON, screenshot e `history.xlsx`.
- **Limite:** prove con fixture QA e servizi locali, senza nuova acquisizione di annunci, esecuzione remota Hermes o deploy. Rispettato il precedente blocco del plugin Browser sulla scheda operativa. I test non certificano accuratezza dei dati di mercato live.

## Aggiornamento locale · Inbox e notifiche · 27 settembre 2026

- **45 flussi browser passati, zero errori JavaScript**, backend HTTP e database temporanei, profilo Chrome separato. Nessun relay o accesso alla scheda operativa. Screenshot Inbox a **320, 393, 768 e 1440 px**, senza overflow del documento; pulsanti testuali non sovrapposti e azioni da almeno 44 px.
- Nuovo feed API paginato a cursore; filtri server per lettura e tipo. Test con **205 eventi**: una notifica non letta fuori dalla vecchia finestra di 200 rimane visibile. Ordinamento stabile per data e ID, anche con timestamp uguali e un nuovo inserimento tra due pagine. Limiti e filtri invalidi rifiutati, eventi dimostrativi esclusi e stato di lettura personale.
- Browser: filtri, lettura singola e globale, apertura dell'immobile, caricamento progressivo e recupero dopo un errore di rete. L'errore conserva le 40 righe caricate; riprova carica la pagina seguente. Focus conservato sui filtri e sulla paginazione; alla fine passa all'elenco. Gli eventi senza destinazione non mostrano un comando di apertura.
- Controller: richieste superate da nuovi filtri, navigazione o logout ignorate; doppi invii bloccati; una lettura confermata ricarica il feed anche quando il refresh generale è già occupato. Il refresh periodico non azzera le pagine già consultate.
- **485 test Python passati, 5 skip**, un warning Starlette/AnyIO. Skip: quattro integrazioni PostgreSQL senza database usa-e-getta e un connettore browser senza eseguibile configurato. **43 test JS**, **23 moduli JS**, **8 controlli mappa**, **7 verifiche API/worker**, compilazione Python e diff-check passati.
- Il primo collaudo ha rilevato una larghezza ereditata di 33 px sui pulsanti testuali dei filtri. Corretta e aggiunta un'asserzione di geometria; l'intera suite browser è stata rieseguita con esito positivo. Conservati i flussi su contatti, scenari, prompt personalizzati, comparabili, ricerca ed export Excel/Word.
- Riscontri locali ignorati da Git: `artifacts/ui-inbox-polish/`, inclusi report JSON, screenshot desktop/mobile ed esportazioni.
- **Limite:** fixture QA e servizi locali; nessuna nuova acquisizione di annunci, esecuzione remota Hermes o verifica della scheda operativa. Nessun deploy. Rispettato il precedente blocco del plugin Browser sulla scheda operativa.

## Aggiornamento locale · comparabili e coerenza dei dati · 27 settembre 2026

- **482 test Python passati, 5 skip**, un warning Starlette/AnyIO. Quattro integrazioni PostgreSQL senza database usa-e-getta e un test del connettore browser senza eseguibile configurato restano esclusi.
- **43 flussi browser passati, zero errori JavaScript**. Backend HTTP, database temporaneo e profilo Chrome separato; nessun relay. Finestra Comparabili verificata con campione vuoto e popolato, a **320, 393, 768 e 1440 px** senza overflow orizzontale del documento.
- L'endpoint Comparabili usa ora il servizio dei riferimenti di mercato per il confronto nello stesso stato manutentivo. Esclude aste, disponibilità ignota/non pubblicata, date future o oltre i 90 giorni, duplicati confermati e asset con evidenze discordanti. Per un soggetto all'asta restituisce un limite esplicito, senza mediana di annunci ordinari.
- Statistiche su tutti gli asset validi entro il limite di 1.000 annunci recenti; massimo 12 righe in UI. Regressione con **18 asset**: mediana **2.450/m²**, 12 righe mostrate e numerosità 18. Le maiuscole nei metadati testati non spezzano il campione.
- Finestra con richiesta e mediana affiancate, differenza percentuale firmata, fonte e data di rilevazione per annuncio, superficie commerciale/lorda/netta, numero di fonti e avvisi. Metodo e fascia centrale apribili da tastiera. Prezzi per m² mostrati fino a due decimali.
- Export Excel scaricato dal browser e riaperto: la voce **Stesso stato** dei fogli Riferimenti e Comparabili coincide con statistiche e ID del campione in piattaforma. Verificati ritorno all'immobile e apertura della scheda di un comparabile. Nessuna nuova valutazione o probabilità di profitto.
- **21 moduli JS**, **37 test JS**, **8 controlli mappa**, **7 verifiche API/worker separati**, compilazione Python e diff-check passati. I test dei campioni ora dichiarano esplicitamente la disponibilità Pubblicato: Unknown non è più un comparabile corrente. Aggiornata l'asserzione Excel per le righe aggiunte del confronto omogeneo.
- Riscontri ignorati da Git: `artifacts/ui-comparables-polish/`, con report JSON, screenshot desktop/mobile e `comparables.xlsx`. Confermati gli altri percorsi del collaudo, inclusi contatti, scenari, ricerca, istruzioni AI ed export.
- **Limite:** nessun deploy, nuova acquisizione o esecuzione remota Hermes. Le prove usano fixture QA; non attestano accuratezza di nuovi annunci reali. Il precedente blocco del plugin Browser sulla scheda operativa rimane rispettato.

## Aggiornamento locale · contatti e richiami · 27 settembre 2026

- **41 flussi browser passati, zero errori JavaScript**, backend HTTP e database temporaneo con profilo Chrome separato. Nessun relay o accesso alla scheda operativa. Schermate del modulo e del riepilogo a **320, 393, 768 e 1440 px** senza overflow orizzontale del documento.
- Ultimo esito separato in interlocutore, data e prossimo contatto; dichiarazione della fonte apribile, distinta dalla verifica del team. Catasto e audit restano disponibili. Note multilinea conservate e indicazioni esplicite per contatti/richiami assenti.
- Esito obbligatorio senza valore preselezionato. Non pertinente disabilita il richiamo e lo esclude dal payload, conservando la data nella bozza per un eventuale cambio di esito. La verifica del mandato mostra un aiuto contestuale e mantiene il controllo server.
- Test di risposta persa: la richiesta POST viene realmente completata sul backend QA, poi la risposta al browser viene interrotta. Tutti i campi e Annulla sono bloccati durante l'invio; dopo l'errore le ipotesi restano presenti e i campi si riabilitano. Il reinvio con lo stesso identificativo lascia **una sola registrazione** nel database.
- Errori vicino alle azioni, portati in vista dopo il rifiuto e rimossi quando l'utente corregge il modulo. Intestazione fissa e pulsante di chiusura da 44 px; campi mobile da 16 px. Nessuna nuova animazione decorativa.
- **475 test Python passati, 5 skip**, un warning Starlette/AnyIO. Skip: quattro integrazioni PostgreSQL senza database usa-e-getta e un test del connettore browser senza eseguibile configurato.
- **20 moduli JS**, **33 test JS**, **8 controlli mappa**, **7 verifiche API/worker**, compilazione Python e diff-check passati. Casi aggiuntivi: nome dell'organizzazione in assenza di nominativo, permessi di sola lettura, dichiarazioni non promosse a verifica, testo escapato e richiamo mancante.
- La prima esecuzione ha rilevato nomi accessibili non stabili sui campi con opzioni/aiuti: corretti. Un secondo percorso del test contatti usava l'esito implicito precedente: aggiornato alla scelta esplicita. Suite completa rieseguita dopo le correzioni.
- Riscontri ignorati da Git in `artifacts/ui-contact-polish/`: report JSON, viste desktop/mobile, file Excel e screenshot dei contatti collegati.
- **Limite:** il blocco del plugin Browser sulla scheda operativa rimane. Il collaudo indipendente usa fixture QA; nessun deploy, acquisizione di nuovi annunci, modifica dei dati operativi o chiamata remota a Hermes.

## Aggiornamento locale · scenario economico · 27 settembre 2026

- **475 test Python passati, 5 skip**, un warning Starlette/AnyIO. Restano esclusi quattro test PostgreSQL senza database usa-e-getta e un test del connettore browser senza eseguibile configurato.
- **39 flussi browser passati, zero errori JavaScript**: backend HTTP e database temporaneo, profilo Chrome separato, nessun relay. Conservati i flussi di ricerca, criteri AI, acquisizione locale, lavorazione, note, contatti, fonti, mappe, selezione ed export.
- Scenario economico riorganizzato in Operazione, Costi e Stress combinato; risultati affiancati sul desktop e sequenziali sul mobile. Intestazione fissa, chiusura da 44 px e comandi visibili durante la compilazione. Schermate e geometria a **320, 393, 768 e 1440 px**; nessun overflow orizzontale del documento.
- Richieste di calcolo mantenute in attesa: Calcola e Salva entrambi disabilitati; un cambio numerico invalida la risposta in ritardo, una modifica al nome conserva il calcolo. Un errore di rete forzato mantiene le ipotesi e riabilita le azioni.
- Salvataggio senza reset del modulo, risultati conservati e successivo comando Salva copia. Apertura di uno scenario con modifiche pendenti: testati annullamento e conferma. Creazione e cancellazione di una copia attraverso le API reali: la bozza in lavorazione rimane intatta.
- Il file Excel esportato viene aperto e confrontato con le ipotesi salvate in piattaforma. Nessuna modifica alle formule del backend o aggiunta di stime probabilistiche. I prezzi massimi e le percentuali mostrano fino a due decimali, senza arrotondamento UI all'intero.
- **20 moduli JS**, **29 test JS**, **8 controlli mappa**, **7 verifiche API/worker separati**, compilazione Python e diff-check passati. Casi unitari aggiuntivi: valuta non EUR senza precompilazione in euro, permessi di sola lettura/autore, massimali non positivi, precisione e nomi escapati.
- L'ispezione degli screenshot ha rilevato chiusura fuori vista e focus sul pannello troppo alto per lo schermo: corretto lo scorrimento e ricollaudato. Riscontri ignorati da Git in `artifacts/ui-scenario-polish/`, con schermata `scenario-overview.png`, viste mobile, report JSON ed Excel.
- **Limite:** il precedente blocco del plugin Browser sulla scheda operativa rimane; nessun tentativo di aggirarlo. Questi test usano esclusivamente l'app QA isolata. Nessun deploy, modifica dei dati operativi o chiamata remota a Hermes; le fixture non attestano nuove opportunità reali.

## Aggiornamento locale · lavorazione e revisioni · 27 settembre 2026

- **475 test Python passati, 5 skip**, un warning Starlette/AnyIO. Quattro integrazioni PostgreSQL senza database usa-e-getta e una prova del connettore browser senza eseguibile configurato.
- **36 flussi browser passati, zero errori JavaScript**, Chrome separato, backend HTTP e database temporaneo. Screenshot dell’elenco, della bacheca e della revisione a **320, 393, 768 e 1440 px**; nessun overflow orizzontale del documento.
- Nuova vista operativa con filtri per fase/responsabile/disponibilità, scaduti e assegnazioni; bacheca conservata. Verificati recupero dallo stato vuoto, scorrimento orizzontale da tastiera, focus dopo cambio vista e controlli touch. La sovrapposizione dei due selettori a larghezza tablet è emersa nel test ed è stata corretta e ricollaudata.
- Una richiesta PUT mantenuta in attesa verifica che i campi siano realmente disabilitati durante il salvataggio. Una modifica concorrente nel database QA produce un vero HTTP 409: nessuna sovrascrittura, bozza conservata, ricaricamento annullabile e versione aggiornata nel modulo.
- API della revisione: fase e versione lette nella stessa query; verificata la coerenza anche dopo modifica dalla scheda immobile e il 404 per record assente. Nessuna migrazione necessaria.
- **19 moduli JS**, **25 test JS** (13 catalogo, 6 lavorazione, 6 riepilogo ricerca), **8 controlli mappa**, **7 verifiche API/worker separati**, compilazione Python e diff-check superati.
- Casi aggiuntivi: scadenza odierna distinta da arretrata, fasi concluse escluse dagli scaduti, filtri combinati, proprietario dell’attività non più disponibile conservato, checklist limitata alle cinque chiavi previste, sola lettura, titoli/nomi escapati e avviso sul limite del workspace.
- Il controllo di scorrimento del test è stato adattato alla CSP esistente, che non consente `unsafe-eval`; nessun cambiamento alla CSP o relay. I campi del modulo hanno nomi accessibili espliciti anche durante il blocco del fieldset.
- Riscontri ignorati da Git: `artifacts/ui-workflow-polish/`, inclusi report JSON, screenshot e file esportati. Il precedente blocco del plugin Browser sulla scheda operativa resta distinto da queste prove indipendenti: nessun nuovo tentativo di accesso alla scheda.
- Nessun deploy, modifica dei dati operativi, acquisizione di mercato o chiamata remota a Hermes. Le immagini mostrano fixture QA; la verifica locale non attesta accuratezza di nuovi annunci reali.

## Aggiornamento locale · archivio e selezione · 26 settembre 2026

- **475 test Python passati, 5 skip**, un warning Starlette/AnyIO. Skip: quattro integrazioni PostgreSQL senza database usa-e-getta e una prova del connettore browser senza eseguibile configurato.
- **34 flussi browser passati, zero errori JavaScript**: Chrome installato, backend HTTP e database temporaneo, senza relay né accesso alla sessione operativa.
- Export verificati aprendo gli XLSX: la selezione mantiene gli ID scelti anche dopo un cambio di comune; l’export dei risultati segue invece i filtri. I due percorsi non dipendono implicitamente l’uno dall’altro. Nessuna selezione vuota viene ampliata all’intero catalogo.
- Confronto disabilitato con uno o più di tre immobili; abilitato con due o tre. Barre nascoste `inert`, selezione fra pagine preservata, stato vuoto recuperabile con Azzera filtri.
- Geometria archivio e selezione a **320, 393, 768 e 1440 px**, comandi mobile da 44 px e notifiche separate dalla barra. Testata compatta in assenza di foto e dopo un vero HTTP 404 per un’immagine del database QA.
- **18 moduli JS**, **13 test catalogo**, **6 test riepilogo ricerca**, **8 controlli mappa**, **7 verifiche API/worker separati**, compilazione Python e diff-check passati. Conservati i flussi su note, contatti, prompt, esecuzioni, scenari, Excel/Word, importazioni, mappe, temi e tastiera.
- La prima iterazione UI si è fermata su un conteggio atteso obsoleto: erano già state aggiunte quattro fixture durante il flusso. Corretta l’asserzione e ripetuta la suite; le schermate hanno inoltre rivelato checkbox impilate e notifiche sovrapposte, corrette e ricollaudate.
- Riscontri locali ignorati da Git: `artifacts/ui-catalog-polish/`, inclusi `catalog-overview.png`, `mobile-selection.png`, report JSON e XLSX filtrato/selezionato.
- Il plugin Browser ha respinto l’accesso alla scheda utente su localhost:3001. Nessun tentativo alternativo di accesso alla scheda. Il collaudo indipendente del progetto usa un’app di test con database e profilo browser temporanei; non certifica lo stato della scheda operativa.
- Nessun deploy, aggiornamento dei dati operativi o chiamata remota a Hermes. I numeri dei record nelle schermate sono fixture di collaudo, non opportunità di mercato verificate.

## Aggiornamento locale · esito ricerca e criteri AI · 26 settembre 2026

- **475 test Python passati, 5 skip**, un warning Starlette/AnyIO. Skip: quattro integrazioni PostgreSQL senza database usa-e-getta e una prova browser senza eseguibile configurato.
- **32 flussi browser passati, zero errori JavaScript**, Chrome installato, backend HTTP e database temporaneo. Nessuna nuova acquisizione o chiamata al modello remoto.
- Nuova regressione API: conteggi AI legati alla singola esecuzione; risposte respinte non incrementano il numero di analisi accettate. Il conteggio non indica corrispondenza ai criteri o correttezza del modello.
- Nuove regressioni UI: istruzioni salvate all’avvio e pagine registrate; task ancora da analizzare; esito parziale; apertura dei pannelli e focus da tastiera conservati dopo un vero aggiornamento SSE/HTTP; chiusura del dialogo passando ai risultati attuali.
- Un requisito coerente e uno incerto rimangono distinguibili nella scheda; citazione apribile e non duplicata nella sintesi. Screenshot della scheda e della ricerca su desktop/mobile; nessun overflow del riepilogo a **320, 393, 768 e 1440 px**.
- **18 moduli JS**, **11 test catalogo**, **6 test del riepilogo ricerca**, **8 controlli mappa**, **7 verifiche API/worker separati**, compilazione Python e diff-check superati. Test JS: raccolta fallita senza attesa fittizia, nessun rapporto 0/0, pending dopo chiusura, sola lettura senza Interrompi, escape del testo e visite deduplicate.
- Browser interattivo: accesso al server QA, apertura da tastiera, istruzioni e percorso consultabili. Le fixture controllate vivono in `backend/tests/support/research.py`; gli screenshot sono prove di collaudo, non dati di mercato.
- Riscontri ignorati da Git: `artifacts/ui-research-evidence/` con report JSON, schermate e export. Nessun hosting, deploy o modifica dei dati operativi. La precisione di Hermes su nuovi annunci resta da misurare con esecuzioni reali.


## Aggiornamento locale · reference e percorso operativo · 26 settembre 2026

- **475 test Python passati, 5 skip**, un warning Starlette/AnyIO. Skip: quattro integrazioni PostgreSQL senza database usa-e-getta e una prova del connettore browser senza eseguibile configurato.
- **30 flussi browser passati, zero errori JavaScript**, Chrome installato e backend HTTP QA isolato. Nessun dato operativo modificato.
- Ricerca in tre sezioni: Asset, Criteri, Ricerca. Verificati persistenza dei filtri chiusi, indicatori delle selezioni e delle istruzioni, riapertura automatica e focus sul campo non valido. Distinti gli errori per istruzioni di navigazione e criteri personalizzati senza runtime compatibile.
- Geometria del modulo a **320, 393, 768 e 1440 px**; regressioni precedenti su scheda, export Excel/Word, contenuti lunghi, tema scuro, tastiera e movimento ridotto conservate.
- Oggi allinea immobile, motivo, contatto e azioni. Provenienza espandibile con nome fonte restituito dall’API; test di parità con il dettaglio. Nella scheda, contatto e quattro riferimenti hanno blocchi distinti; catasto e storico restano accessibili tramite disclosure, verificata anche nel browser interattivo.
- **17 moduli JS**, **11 test catalogo**, **8 controlli mappa**, **7 verifiche API/worker separati**, compilazione Python e diff-check superati.
- Reference generata con imagegen integrato e implementata in HTML/CSS. Materiale di design ignorato da Git: `artifacts/design-reference/vedra-workflow-reference.png` e `prompt.txt`. I dati illustrativi della reference non sono stati inseriti nel prodotto.
- Riscontri ignorati da Git: `artifacts/ui-reference-workflow/`, con report JSON, schermate desktop/mobile e file esportati.
- Nessuna nuova acquisizione di mercato, chiamata al modello remoto o distribuzione. Il collaudo locale verifica interfaccia, persistenza e contratti, non l’accuratezza dei dati reali né l’esecuzione remota delle istruzioni da parte di Hermes.

## Aggiornamento locale · layout della scheda · 26 settembre 2026

- **475 test Python passati, 5 skip**, un warning Starlette/AnyIO. Skip: quattro integrazioni PostgreSQL senza database usa-e-getta e una prova del connettore browser senza eseguibile configurato.
- **29 flussi browser passati, zero errori JavaScript** usando Chrome installato e backend HTTP QA isolato. Nessun dato operativo modificato.
- Nuove verifiche geometriche a **320, 393, 768 e 1440 px**: Excel/Word sulla stessa riga e vicini, prezzo prima delle azioni, nessun overflow del dialogo, mobile a tutta larghezza, export con altezza minima 44 px. Entrambi i file scaricati e aperti nei test (XLSX e DOCX).
- Stress con titolo lungo, stringa senza spazi e prezzo di nove cifre; metodo della priorità apribile con Enter, chiusura con Escape. Verificati anche tema scuro, movimento ridotto e flussi precedenti.
- Browser interattivo: individuati e corretti il limite di larghezza nativo del dialogo e l’intestazione storico che debordava a 320 px; focus restituito al pulsante dell’immobile e console senza errori.
- **17 moduli JS**, **11 test catalogo**, **8 controlli mappa**, **7 verifiche API/worker separati**, compilazione dello script UI e diff-check superati.
- Riscontri ignorati da Git: `artifacts/ui-layout-polish/`, incluse schermate desktop/mobile, `long-content-mobile.png`, `property.xlsx`, `property.docx` e report JSON.
- Nessuna nuova acquisizione di mercato, prova del modello remoto o distribuzione. Il collaudo di layout non attesta precisione di Hermes o qualità dei dati reali.

## Aggiornamento locale · preparazione del contatto · 26 settembre 2026

- **475 test Python passati, 5 skip**: quattro integrazioni PostgreSQL senza database usa-e-getta e una prova del connettore browser senza eseguibile configurato. Un warning Starlette/AnyIO.
- **27 flussi browser passati, zero errori JavaScript**, Chrome installato, backend HTTP locale e database QA temporaneo. Desktop 1440 px, mobile 393 px, tema scuro e movimento ridotto.
- **17 moduli JS**, **11 test catalogo**, **8 controlli mappa**, **7 verifiche API/worker separati**, compileall e diff-check superati.
- Otto nuove regressioni: scadenza per fonte e confine esatto, date mancanti/errate/future, catalogo recente senza dettaglio, importazione distinta dalla verifica, contatto condiviso senza trasferire il mandato e domande coerenti con i dati disponibili. Parità API/Excel delle domande e provenienza dell’annuncio contattato.
- La coda sposta i dettagli scaduti tra i casi da ricontrollare senza modificarne la disponibilità. La scheda mostra il contatto più recente su un annuncio collegato e permette di aprire il record originale.
- Browser interattivo: domande apribili da tastiera, nessun errore console e nessun overflow del documento a 393 px. Le domande restano chiuse inizialmente.
- Riscontri ignorati da Git: `artifacts/ui-contact-readiness/`, con report, workbook e schermate `contact-preparation`, `mobile-contact-preparation` e `stale-before-contact`.
- Revisione dei requisiti in `docs/REQUIREMENTS_REVIEW.md`. Nessuna nuova acquisizione di mercato, chiamata remota a Hermes, modifica di hosting o distribuzione; i dati QA non provano l’accuratezza del mercato. Nessuna probabilità di profitto introdotta.

## Aggiornamento locale · filiera e scenari · 26 settembre 2026

- **467 test Python passati, 5 skip**: quattro integrazioni PostgreSQL senza database usa-e-getta e una prova del connettore browser senza eseguibile configurato. Un warning Starlette/AnyIO.
- **26 flussi browser passati, zero errori JavaScript** con backend HTTP locale e dati QA. Verificati filtri economici/contatto, salvataggio e ricaricamento delle ipotesi, export degli stessi scenari, invalidazione dei risultati al cambio input, oltre ai flussi precedenti.
- **17 moduli JS**, **11 test catalogo**, **8 controlli mappa**, **7 verifiche API/worker separati**, compileall e diff-check superati.
- Contratti: dichiarazioni dirette esplicite, negazioni e casi ambigui; recapito obbligatorio nella modalità restrittiva; prezzi in linea o benchmark assente non qualificano; priorità al contatto diretto anche tra annunci dello stesso asset; brief Hermes con vincoli strutturati.
- Calcolo: ROI obiettivo, tetto d’acquisto arrotondato per difetto, stress simultaneo su prezzo/lavori/durata, stress nullo uguale al caso base, input non finiti respinti, tetto negativo esplicito. Parità API, scenario ricaricato e foglio Excel Scenari.
- Browser interattivo: risposta ritardata di 4 secondi non sovrascrive input modificati; scenario in perdita e nessun acquisto positivo raggiungibile; 393 px senza overflow del documento. Fault injection e server QA arrestati dopo il controllo.
- Correzioni: export singolo ora include scenari salvati; etichetta accessibile del filtro contatto; caricamento di vecchi scenari ripristina anche i nuovi parametri; risultati invalidati durante la modifica e risposte tardive ignorate.
- Riscontri ignorati da Git: `artifacts/ui-investment-decision/`, incluse schermate, `scenario.xlsx` e report. L’Excel è un’istantanea dei risultati della piattaforma, non una funzione analitica separata.
- Nessuna acquisizione reale nuova, verifica del mandato, chiamata modello remota o distribuzione. I test del brief non provano l’esecuzione effettiva di ogni istruzione da parte di Hermes. Nessuna Monte Carlo o probabilità di profitto dichiarata.


## Aggiornamento locale · evidenze incrociate · 26 settembre 2026

- **445 test Python passati, 5 skip**. Quattro integrazioni PostgreSQL senza database temporaneo; una prova del connettore browser senza eseguibile specificato. Un warning Starlette/AnyIO, nessun errore.
- **17 moduli JS**, **11 test catalogo**, **8 controlli mappa**, compilazione Python e **7 controlli API/worker separati** passati. Diff senza errori di spaziatura.
- **24 flussi browser passati, zero errori JavaScript** su backend HTTP reale e database QA isolato: desktop 1440 px, mobile 393 px, tema scuro, movimento ridotto e precedenti flussi completi.
- Nuove prove: dossier dello stesso asset, recapiti distinti, prezzo discordante, quartili, fonti per dominio, mediana solo da campione sufficiente, scarto solo sullo stesso stato manutentivo, esclusione dei comparabili contestati, identità contraddittorie, disponibilità discordante e richiami fra annunci collegati.
- Excel: nove fogli, riferimenti arricchiti e nuovo confronto fra fonti. Storico senza false variazioni al cambio di valuta, operazione o in presenza di prezzi mancanti.
- Browser interattivo: passaggio alla seconda fonte e ritorno, apertura tabella OMI, chiusura definitiva del dialogo, 393 px senza overflow del documento, nessun errore in console. Dettagli tecnici apribili; i quattro riferimenti precedono il benchmark di screening.
- Riscontri locali ignorati da Git: `artifacts/ui-evidence-aggregation/` con report, screenshot e workbook `decision.xlsx`. I dati popolati sono fixture riconoscibili come QA, mai caricati nel workspace operativo.
- Nessuna nuova acquisizione di mercato, chiamata modello remota o distribuzione. I collegamenti fra annunci sono confermati dal team: il collaudo non prova un riconoscimento automatico dell’identità o accuratezza di mercato. Fonti distinte non equivalgono a informazioni indipendenti.


## Aggiornamento locale · ricerca e contatti · 26 settembre 2026

- **437 test Python passati, 5 skip**: quattro integrazioni PostgreSQL senza database usa-e-getta configurato; una prova del connettore browser senza eseguibile specificato. Un warning di deprecazione Starlette/AnyIO, nessun errore.
- **17 moduli JavaScript** verificati sintatticamente; **11 test catalogo**, **8 controlli mappa**, **7 controlli API/worker separati** passati.
- **23 flussi browser passati, zero errori JavaScript**: Chrome desktop 1440 px, mobile 393 px, tema scuro, movimento ridotto, stati vuoti, ricerca, filtri, selezione, Excel, contatti, lavorazione, importazioni e configurazione fonti. Backend HTTP reale, database e annunci esclusivamente di test.
- Contratti nuovi: istruzioni multilinea, verifica per requisito, citazioni del broker, invalidazione su cambio contatto, pagina iniziale effettivamente acquisita, snapshot della configurazione e consegna univoca del brief, URL fuori perimetro respinti, recapiti associati all’annuncio, negazioni conservate, date future respinte, ledger idempotente, viewer escluso dalle scritture, richiami, annunci chiusi e Excel sicuro.
- Ribassi conteggiati solo tra prezzi consecutivi con valuta e operazione note e identiche. Valori mancanti interrompono il confronto; prima rilevazione e pubblicazione dichiarata restano distinte.
- Controlli Browser interattivi aggiuntivi: modulo ricerca multilinea a 393 px senza overflow; errore recuperabile senza perdere i testi; mandato senza nota respinto; contatto salvato; risposta immobile ritardata di 4 secondi dopo chiusura non sovrascrive un nuovo modulo.
- Correzioni emerse dal collaudo: etichette univoche dei select, archivio aperto conservato dopo refresh, data richiamo senza ora, rivalidazione dei moduli JS non versionati per evitare UI e azioni di versioni diverse.
- Riscontri locali esclusi da Git: `artifacts/ui-decision-workflow/` (report, schermate, Excel), anteprima interattiva con database temporaneo separato. I risultati non provano nuove acquisizioni di mercato né l’accuratezza del modello remoto.
- Nessun deploy, push, modifica di hosting o chiamata al modello sulla VPS. Parità PostgreSQL e accuratezza operativa Hermes richiedono verifiche dedicate; non sono dichiarate superate dagli skip o dalle fixture.

## Aggiornamento locale · criteri e selezione · 26 settembre 2026

- Python: **425 passati, 5 skip**. Quattro integrazioni PostgreSQL senza `TEST_DATABASE_URL`; una prova specifica del connettore browser senza `BROWSER_TEST_EXECUTABLE`.
- Frontend: **16 moduli** con sintassi valida, **11 test catalogo**, **8 invarianti mappa**.
- Processi separati API/worker: **7 controlli** passati.
- Browser: **22 flussi passati, zero errori JavaScript**, Chrome locale con backend HTTP e database temporaneo. Desktop 1440 px, mobile 393 px, tema scuro, movimento ridotto, stati vuoti, download Excel, errore recuperabile sui criteri senza motore AI.
- Nuovi contratti: prompt salvato e trasmesso, citazioni estranee respinte, esiti incerti fuori filtro, isolamento fra prompt, invalidazione su modifiche, riaccodamento delle analisi, testo troncato, vincoli numerici, campioni omogenei, esclusioni e deduplicazione, Excel e formule sicure.
- Riscontri locali ignorati da Git: `artifacts/ui-client-features/`, incluso `property.xlsx`. I dati e le risposte del modello nel collaudo sono fixture di test, non nuove acquisizioni sul mercato.
- Nessuna nuova chiamata al modello remoto, distribuzione, modifica di hosting o verifica operativa dei portali in questa fase. Gli skip non attestano parità PostgreSQL né accesso ai portali.


Data: 18 settembre 2026. Base GitHub verificata:
`f1a47fc1c5873992ab6cbb99e56770dfc141d2dc` (0.3.0).

## Risultati effettivi

| Verifica | Risultato locale |
|---|---|
| Suite Python | **296 passati, 4 saltati** |
| Nuovi test archivio/collaborazione/storia | **46 passati** |
| JavaScript | **14 moduli** con sintassi valida |
| Frontend funzionale | **7 test**: concorrenza, cancellazione, errori, debounce, selezioni e login senza sessione |
| Mappa | **8 invarianti** passate |
| API + worker separati | **7 controlli** passati, processi reali |
| UI + backend HTTP locale | **18 gruppi di flussi**, nessun errore JavaScript |
| Python compileall | Passato |
| Build Vercel | Output generato con origin HTTPS di test; non è un deployment |

I quattro skip sono integrazioni PostgreSQL: qui mancano il server e i driver
opzionali. La CI `postgres` contiene ora anche la prova di ricerca, storia e batch
review. Deve passare realmente prima del merge insieme alla job `tests`; né gli
skip né l’assenza dei check sono considerati successo dal helper PR.

## Prove della 0.4

Un archivio di **2.006 annunci sintetici di test** verifica la lettura dei record oltre
il precedente limite, la navigazione in 21 pagine senza duplicati su un database
fermo, i conteggi, le opzioni geografiche e gli export filtrati. L’esportazione troppo
ampia viene rifiutata: non produce un file apparentemente completo ma troncato.

Filtri parametrizzati, caratteri %, _, ! e apostrofi letterali; no interferenza di
sintassi SQL, valute obbligatorie nei range economici, valori non finiti rifiutati,
superfici mancanti, filtri combinati e qualificazione riferita allo specifico agente.
Record sintetici legacy esclusi; proiezione delle strategie coerente con le analisi.

Revisione multipla: rollback completo in caso di record/versione in conflitto, nessuna
nota o audit parziale, no-op, nota obbligatoria per scarto, conservazione di responsabile,
scadenza e checklist, permessi viewer e CSRF. Trasferimento di indici e osservazioni
verso un DB vuoto, rollback del target non vuoto, migrazione ripetibile.

Cronologia: confronto dei valori effettivamente registrati, nessuna modifica ai dati
passati dopo una nuova analisi, pagina con predecessore corretto, cursore limitato
all’immobile, valuta precedente e successiva e mancata retro-compilazione delle
vecchie osservazioni. Un’acquisizione invariata non crea una storia fittizia.

Preflight: runtime senza chiavi, fonte assente/disabilitata, allowlist, permesso,
browser, cooldown futuro/malformato, worker assente e import statico. Nessuna richiesta
HTTP o modello per la diagnostica. Una nuova configurazione invalida il vecchio test
fonte senza cancellare il backoff operativo.

## Interfaccia e trasporto del test

Collegamento reale al backend locale: login, import, note, scenari, comparabili,
revisione, pipeline, selezione tra pagine, batch edit, filtri avanzati, errore 422
correggibile, cronologia, agenti con job eseguito, pausa/ripresa, mappa, viste salvate,
fonte, diagnostica, tema scuro, mobile 393 px e reduced motion. Selezione anche nelle
schede e conservazione del focus. Il controller ha ulteriori test Node per risposte
fuori ordine e annullamento: un vecchio errore non copre risultati più recenti.
Il rendering della schermata di accesso viene verificato anche senza stato autenticato
o DOM, a copertura di una regressione individuata e corretta nel collaudo del pacchetto.

La navigazione diretta di Chromium è bloccata con `ERR_BLOCKED_BY_ADMINISTRATOR`.
Il parametro `--relay` inoltra le richieste al **backend HTTP reale**, non a risposte
API simulate. I cookie sono gestiti dal client HTTP e la CSP è omessa nel relay:
**non è una validazione di cookie del browser, CSP, HTTPS o proxy Vercel**. In CI e
nell’ambiente destinatario usare il test senza `--relay`.

Inter è configurato, ma il caricamento remoto è disabilitato nel collaudo: le immagini
usano il fallback di sistema. Nessun file font è incluso. Gli screenshot di release
mostrano stati vuoti; le prove popolate usano fixture sintetiche sotto `backend/tests`,
mai seed o annunci fittizi nel runtime. Nessun modello ha generato quei risultati QA.

## Processi e riproduzione

Il test processi avvia API e worker separatamente su database temporaneo: archivio vuoto,
import, coda, worker consumatore, secondo worker respinto, seconda run senza duplicati,
arresto osservabile e riconnessione. Non è una prova di continuità per giorni.

```bash
python -m pytest -q
python -m compileall -q backend hermes scripts
node scripts/check_frontend.mjs
node scripts/test_map.mjs
node scripts/test_catalog.mjs
python scripts/test_worker_processes.py
python -m playwright install chromium
python scripts/test_ui.py
```

Nell’ambiente ristretto usato per questo lavoro:
`python scripts/test_ui.py --chromium /usr/bin/chromium --relay`.

## Limiti e pubblicazione

Non testati: PostgreSQL reale, Supabase remoto, Vercel/HTTPS, Docker, SMTP, scraping
di portali reali, Hermes/provider AI reali e funzionamento per giorni. Il prodotto
rimane un’istanza dedicata per cliente, senza billing, self-signup o multitenancy
condivisa dichiarati. I test di classificazione verificano contratti ed evidenze,
non la qualità di un modello su un portafoglio immobiliare reale.

Il connettore GitHub di questa sessione offre letture, non scritture. Git dal container
non risolve github.com e GitHub CLI non è disponibile. Nessuna PR, push o merge è stato
eseguito. `scripts/publish_pr.py` è predisposto con base 0.3 corretta e branch 0.4,
senza override amministrativi. La verifica del pacchetto è in `PACKAGE_CHECK.txt`.

## Copia estratta

La suite è stata rieseguita dalla copia estratta: **296 passati, 4 saltati**.
Dopo la correzione della regressione nel login sono stati rieseguiti con successo
tutti i **18 gruppi UI** e i **7 controlli API/worker**. Il manifest e la patch
permettono di confrontare esattamente i sorgenti distribuiti.

## 2026-09-23 — browser navigation and UI states

- Full suite with `BROWSER_TEST_EXECUTABLE` set to the installed Chrome: 362 passed,
  4 PostgreSQL tests skipped (no disposable PostgreSQL URL configured).
- Native Chromium integration rechecked after redirect interception: JavaScript
  discovers the link, the detail is persisted, a same-source redirect succeeds,
  and redirects outside the source or into a robots-excluded path are rejected
  before those fixture endpoints receive a request.
- 19 real-HTTP local UI scenarios passed, including source browser-setting
  persistence, desktop/mobile, reduced motion and dark mode; no page errors.
- 7 separate-process checks, 15 JS module syntax checks, 8 map invariants and
  7 catalog tests passed.
- The browser integration check uses an isolated local fixture server. It is not
  evidence of portal coverage, a model call, or a production deployment.
- Production API and existing Hermes toolset remain reachable. The new seven-tool
  profile and frontend have not been deployed in this pass; live activation waits
  for administrative access. No secrets or real listing contents enter the package.

## 2026-09-23 — verifica dopo l'attivazione live

- 362 test Python passati, quattro integrazioni PostgreSQL saltate in assenza di
  un database temporaneo configurato. La prova Chromium include ora 30 script
  statici e mantiene i controlli sui redirect prima del contatto con la destinazione.
- 15 moduli JavaScript, 8 invarianti mappa, 7 test catalogo e 7 controlli dei processi
  passati nuovamente.
- Verifica interattiva su backend HTTP locale isolato: login, attesa Hermes con
  conteggi ancora assenti, interruzione, mobile a 393 px e tema scuro. Nessun
  overflow orizzontale o errore JavaScript osservato. I dati sono fixture QA,
  non annunci reali e non sono stati trasferiti al workspace operativo.
- L'ultimo collaudo UI completo (19 scenari) precede questa correzione circoscritta.
- Runtime live a sette tool verificato; ricerca fallita per timeout del provider.
  Il login visivo live non è stato completato in questa verifica.

- Dopo il deploy della correzione il test fonte con browser nativo è passato
  (catalogo, 10 link nella prima pagina e un dettaglio). Nove endpoint live
  rispondono HTTP 200; scheduler ogni 360 minuti attivo; hash degli asset UI
  pubblicati uguali ai sorgenti verificati. Non è un ciclo Hermes completato.

## 2026-09-23 — ricerca browser e seconda fonte

- Ciclo Hermes live completato: 20 link scoperti, quattro acquisizioni/verifiche,
  tre aggiornamenti, zero errori. Gli annunci venduti sono stati riconosciuti
  autonomamente. Nessun risultato compatibile con il budget in quella fonte.
- 372 test Python passati con Chromium; quattro test PostgreSQL saltati senza
  database temporaneo. Dieci regressioni coprono località esplicite, stato,
  negazioni e precedenza dei dati strutturati.
- 15 moduli JS, otto controlli mappa, sette test catalogo e sette controlli dei
  processi passati. Collaudo UI mirato su HTTP locale: menu mobile escluso
  dall'accessibilità quando chiuso, navigazione, schede agenti a 393 px senza
  contenuti tagliati, tema scuro. Fixture isolate, mai trasferite in produzione.
- Aggiunta configurazione ABE con provenienza per comune/zona e disponibilità.
  Estrazione locale verificata su una pagina pubblica; attivazione e acquisizione
  Hermes della seconda fonte da verificare dopo il deploy.

- Seconda fonte verificata sul server: otto link nel catalogo e 20 immagini
  estratte dal DOM dinamico. Primo ciclo Hermes sulle due fonti completato:
  tre nuovi immobili, zero errori, uno compatibile; due richiedono correzione
  dell'estrattore di località prima di poter essere valutati nei criteri.
- Collaudo autenticato live: schede e immagini, priorità, scenario economico
  calcolato senza salvare ipotesi di prova, export Word valido. Nove endpoint
  HTTP 200 e programma a sei ore confermato.
- Dopo le correzioni: 378 test Python passati nella suite; il solo test Chromium
  richiedeva l'apertura di una porta localhost vietata dalla sandbox ed è passato
  con l'esecuzione autorizzata (379 complessivi). Quattro integrazioni PostgreSQL
  restano saltate. Il refresh dei campi essenziali e le intestazioni alternative
  hanno regressioni dedicate.
- Il ricontrollo live ha riacquisito dalla fonte i due record privi di località:
  comune e zona sono ora presenti e tre annunci rientrano nei criteri. Nessuna
  modifica manuale ai record. Immagini, filtro agente e punteggio operativo
  verificati nell'interfaccia autenticata.
- Verifica responsive live: contenuto e schede senza overflow a 393 px; larghezza
  DOM coerente a 1440 px. Foto caricate senza segnaposto contraddittorio; testi
  finali e quattro asset pubblicati uguali ai sorgenti. L'acquisizione della
  schermata completa a 1440 px non è riuscita nello strumento browser.
- Ultimo ciclo Hermes completato: 28 link, quattro acquisizioni/verifiche, due
  aggiornamenti, tre immobili compatibili e zero errori. Analisi validate per
  i record aggiornati. Entrambe le fonti consultate tramite browser.
- Consultazione OMI live verificata nell'interfaccia: provincia, comune, zona,
  tabella ufficiale e semestre esposti; nessun benchmark assegnato arbitrariamente
  agli immobili privi di coordinate o base di superficie omogenea.

## 2026-09-23 · Periodic discovery and asynchronous UI

- Backend: 387 passed, four PostgreSQL cases skipped (no disposable database),
  plus the separately executed real Chromium integration passed: 388 total.
- New regressions cover a verified discovery with no acquisitions, incomplete
  Hermes protocol, all-source failure, partial failure, and recent/closed records
  not consuming the new-listing allowance. Required refreshes remain enforced.
- JavaScript: 16 modules parse; 8 map and 7 catalog checks pass.
- Separate API/worker process test: all seven lifecycle checks pass.
- Isolated browser fault injection delays detail/run/scenario requests by four
  seconds. Closing an in-flight run and opening agent configuration preserves the
  new dialog after the old response arrives. No production data used for this test.
- Live scheduled-cycle and final UI evidence are recorded separately after deploy.

- Additional agent-sharing regression passes: a listing known to another agent
  is still acquired and linked to the requesting agent. Total backend coverage
  executed locally is 389 passing checks (four PostgreSQL cases skipped locally).
- Browser checks also passed for a scenario closed during calculation, empty query,
  filter reset, rapid query replacement, a three-record comparison and live mobile
  catalog layout (393 px, three qualifying records, no document overflow).
- Offline testing found stale pagination counts and enabled selection actions.
  Corrected with two further catalog regressions: nine JS catalog checks pass.
- CI exposed missing Pillow in the declared application dependencies; the locally
  validated version is now pinned. UI heading assertions follow the shortened copy.

- Live scheduler proof: an existing six-hour agent was made due once without
  calling the manual enqueue endpoint. The worker started a `schedule` run at
  16:12 UTC and completed it at 16:21 UTC: two sources, 28 catalog links, zero new
  acquisitions, zero source errors. The next run was automatically set six hours
  after completion. No listing facts or agent criteria were manually changed.
- Browser offline recovery succeeds after retry; no previous count or actionable
  page selection is shown while results are unavailable. Manual double-click
  starts one queued run, and cancellation is visible in its detail.
- CI's end-to-end UI pass caught a result-container lookup outside the scenario
  form. It is now scoped to the owning dialog, retaining the closed-form guard.
- The corrected scenario calculation was verified in the browser with purchase
  100,000, sale 160,000, works 20,000, 10% contingency and 3% selling costs:
  capital 122,000, profit 33,200, simple ROI 27.21%. Save persisted that result in
  the isolated QA database. Production received no test financial assumptions.

## Portali e configurazione fonti — 23 settembre 2026

- 402 test Python passati, 5 skip locali: 4 PostgreSQL e 1 Chromium nativo
  privo di eseguibile esplicito in questo passaggio.
- 14 regressioni per profili dei portali, località, prezzi multiunità, JSON-LD
  estraneo, URL duplicati, paginazione e preset senza attivazione implicita.
- 16 moduli JavaScript, 8 controlli mappa, 9 catalogo e 7 processi separati passati.
- Browser locale: cambio dei tre preset, autorizzazione non preselezionata,
  creazione fonte nel solo database di test e errore di acquisizione leggibile.
- Pagine pubbliche dei tre portali consultate nel browser; accesso dal browser
  della VPS negato con HTTP 403 su tutti e tre. Nessuna acquisizione automatica
  generalista dichiarata riuscita.

## 2026-09-27 · Dati per decidere (feedback Jacopo e Valentina)

- Backend: 526 passati, 6 skip PostgreSQL (nessun `TEST_DATABASE_URL`). Nuovo
  `test_signals.py`: anzianità dichiarata/prima rilevazione, date future ignorate,
  ribassi omogenei, delta sui tre campioni e OMI, contatti, vista `reduced`,
  ordinamento `listed`, Excel allineato, query per pagina limitate ai segmenti.
- JavaScript: 34 moduli validi; `test_signals_ui.mjs` 8/8 (testi dei delta, “≥”
  per l’età non dichiarata, ordine dei confronti, escaping, scala senza dati);
  tutte le altre suite `.mjs` verdi, mappa 8/8, processi separati passati.
- Browser (`test_ui.py`, Chromium locale 1200): 62 controlli passati, nessun errore
  di pagina, nessun overflow 320–1440 px. Aggiornate due asserzioni per testi
  cambiati di proposito (“annunci”, contatore dei filtri avanzati).
- Verifica manuale su database QA temporaneo (fixture dei test più date di
  pubblicazione e ribassi sintetici): Oggi, Immobili, scheda chiara/scura e 393 px,
  Duplica ricerca, Excel della scheda. Nessun deploy e nessun dato del cliente usato.
