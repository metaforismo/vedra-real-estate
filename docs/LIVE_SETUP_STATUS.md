# Stato delle verifiche

## Ricerca guidata da Hermes

Implementata ricerca nelle fonti HTML configurate, selezione degli URL da parte
dell'agente, acquisizione dei dati verificata dal backend e analisi con evidenze.
Il profilo espone sei strumenti MCP ristretti. La ricerca copre le fonti selezionate,
non l'intero mercato. I dettagli sono in HERMES.md.

Verifica locale della revisione a1696f4: 309 test Python passati, 4 test PostgreSQL
non eseguiti localmente, 14 moduli JavaScript verificati, 8 controlli mappa,
7 test catalogo, 7 controlli API/worker separati e 18 scenari UI desktop/mobile.
Le fixture dei test non sono dati operativi né prove di acquisizione live.

## Collaudo di un'installazione

Il deploy della nuova acquisizione e il suo collaudo end-to-end restano da completare.
Una precedente verifica di hosting e classificazione non dimostra acquisizione online.
Prima di dichiarare pronta un'installazione verificare:

- Ricerca avviata dall'interfaccia e chiamate effettive ddell'agente.
- Acquisizione e persistenza di annunci con URL e data della fonte.
- Seconda ricerca con aggiornamento e deduplica.
- Errori, cancellazione, riavvio worker e periodicità.
- Esperienza desktop/mobile, stati vuoti e dati incompleti.
- Backup e ripristino su database separato.

Conservare URL privati, indirizzi delle VM, account, identificativi di deployment,
run e credenziali fuori dal repository e dalla descrizione della PR.
