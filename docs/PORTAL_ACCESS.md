# Accesso ai portali

Verifica HTTP del 21 settembre 2026. Non equivale a una verifica nel browser
né a una copertura attiva del mercato. Un HTTP 403 del connettore non dimostra
che sia obbligatoria un'API: navigazione browser e accesso API sono percorsi distinti.
Hermes ricerca soltanto sulle fonti abilitate, assegnate all'agente e autorizzate
nel server. Un errore di una fonte non interrompe la ricerca sulle altre;
la fonte fallita resta visibile nel registro. Se falliscono tutte, la raccolta
non viene dichiarata completata.

| Portale | Verifica HTTP | Percorso alternativo documentato, non obbligatorio |
| --- | --- | --- |
| Immobiliare.it | Ricerca HTML: HTTP 403 con il connettore Vedra | Accesso dati autorizzato; verificare gli endpoint di ricerca/comparabili di Insights |
| idealista | Ricerca HTML: HTTP 403 con il connettore Vedra | Search API, previa concessione delle credenziali e verifica della copertura italiana |
| Casa.it | Ricerca HTML: HTTP 403 con il connettore Vedra | Feed o accordo dati con il portale/gestionale |
| Wikicasa | Ricerca HTML accessibile; condizioni vietano la copia senza consenso scritto | Servizio dati o autorizzazione scritta |
| Subito | Il robots.txt richiede espressamente un permesso per accesso automatico | Autorizzazione del portale |

Nessuna di queste fonti è presentata come collegata. Non sono stati creati account,
accettati contratti, inviati messaggi o acquistati servizi.

## Navigazione affidata a Hermes

Il profilo attuale espone sei strumenti MCP per ricerca e acquisizione HTML.
Non espone ancora navigazione interattiva, filtri o sessioni autenticate dei portali.
Il rendering opzionale del connettore passa attraverso lo stesso client HTTP:
non costituisce una prova di navigazione con la rete nativa di Chromium.

La futura integrazione browser deve conservare lo stesso contratto di evidenza:
Hermes sceglie le azioni, il codice cattura la pagina effettivamente visitata e
valida i fatti prima di salvarli. Fonte, URL, data e stato devono restare verificabili.
Una pagina di login, un CAPTCHA o un errore non sono un catalogo vuoto.
Le sessioni devono appartenere al profilo del workspace, senza riutilizzare
credenziali personali o inserire cookie nei prompt. Un account non garantisce
che il portale consenta l'accesso automatizzato.

Riferimenti del fornitore:
- https://www.immobiliare.it/insights/dati-api/
- https://insights.immobiliare.it/webdocs/
- https://www.immobiliare.it/terms/
- https://developers.idealista.com/access-request
- https://www.wikicasa.it/dati
- https://www.wikicasa.it/condizioni-generali
- https://www.subito.it/robots.txt

L'API di pubblicazione annunci di un gestionale non implica accesso agli annunci
di tutto il portale. Prima di implementare un adapter verificare il contratto di
lettura effettivo: endpoint, autenticazione, campi, paginazione, limiti, diritto di
conservare foto/testi, stato di disponibilità e cancellazioni. Credenziali soltanto
sul server; mai nel browser, nei prompt di Hermes o nel repository.

## Testo per richiedere un accesso dati (bozza, non inviato)

Stiamo realizzando una piattaforma di ricerca immobiliare per un cliente
professionale. Cerchiamo un accesso autorizzato agli annunci in Italia, filtrabili
per comune, tipologia, prezzo e superficie, con aggiornamenti di prezzo e stato,
URL della fonte e identificativo stabile. Il processo effettua verifiche periodiche
ogni sei ore. Vorremmo conoscere copertura, disponibilità di ambiente di prova,
limiti, costi e diritti di visualizzazione/conservazione di testi e immagini.
