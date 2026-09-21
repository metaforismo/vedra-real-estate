# Accesso ai portali

Verifica del 21 settembre 2026. Non equivale a una copertura attiva del mercato.
Hermes ricerca soltanto sulle fonti abilitate, assegnate all'agente e autorizzate
nel server. Un errore di una fonte non interrompe la ricerca sulle altre;
la fonte fallita resta visibile nel registro. Se falliscono tutte, la raccolta
non viene dichiarata completata.

| Portale | Verifica pubblica | Collegamento necessario |
| --- | --- | --- |
| Immobiliare.it | Ricerca HTML: HTTP 403 con il connettore Vedra | Accesso dati autorizzato; verificare gli endpoint di ricerca/comparabili di Insights |
| idealista | Ricerca HTML: HTTP 403 con il connettore Vedra | Search API, previa concessione delle credenziali e verifica della copertura italiana |
| Casa.it | Ricerca HTML: HTTP 403 con il connettore Vedra | Feed o accordo dati con il portale/gestionale |
| Wikicasa | Ricerca HTML accessibile; condizioni vietano la copia senza consenso scritto | Servizio dati o autorizzazione scritta |
| Subito | Il robots.txt richiede espressamente un permesso per accesso automatico | Autorizzazione del portale |

Nessuna di queste fonti è presentata come collegata. Non sono stati creati account,
accettati contratti, inviati messaggi o acquistati servizi.

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
