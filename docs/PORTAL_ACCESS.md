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

## Canali legittimi per immobiliare.it, idealista e Casa.it

I tre portali bloccano l'accesso automatico (HTTP 403, verifiche anti-bot). Vedra
**non** li aggira: niente browser "stealth", fingerprint alterati, proxy residenziali o a
rotazione, risoluzione di CAPTCHA, né alcuna richiesta del server verso i portali.
`SafeFetcher` rifiuta i loro domini anche se qualcuno li aggiunge a `LIVE_ALLOWED_DOMAINS`,
e Scout non li apre. Gli annunci entrano solo da due canali in cui è il portale, o una
persona, a consegnare i dati:

1. **Avvisi dei portali (email).** Il team salva le ricerche sul portale con gli avvisi
   inviati a una casella dedicata. Vedra legge le email caricate in Fonti (file `.eml`) oppure,
   se configurata (`ALERTS_IMAP_*`), la casella in sola lettura: `EXAMINE`, `BODY.PEEK`,
   nessun flag modificato, nessuna cancellazione. La password resta nell'ambiente del server,
   mai nel database, nell'interfaccia o nei log.
2. **Vedra Capture su una pagina di risultati.** Chi sta guardando una pagina di risultati
   del portale preme "Invia a Vedra": l'estensione invia il DOM della scheda aperta e Vedra
   importa ogni annuncio visibile. Nessuna navigazione, scorrimento, paginazione o clic per
   conto della persona. Le pagine di dettaglio seguono il flusso esistente.

Regole comuni (`backend/app/services/portal_cards.py`):

- contenuto non affidabile: si legge l'HTML con BeautifulSoup, nessuna immagine remota
  caricata; l'URL della foto resta un riferimento testuale;
- un link vale solo se corrisponde all'URL di un annuncio del portale
  (`/annunci/<id>/`, `/immobile/<id>/`, `/immobili/<id>/`). I link di tracciamento vengono
  decodificati dai loro parametri (percent-encoding, base64) e **mai aperti**; `javascript:`,
  `data:` e domini simili non valgono. Una scheda senza URL recuperabile è saltata e contata;
- ogni valore (prezzo, prezzo precedente in caso di ribasso, m², locali, bagni, indirizzo,
  comune) deve essere scritto nel testo della scheda; due prezzi o due superfici senza
  indicazione esplicita non producono alcun valore;
- email accettate solo da mittenti nell'elenco `ALERTS_SENDER_DOMAINS` (anche inoltrate
  come allegato `message/rfc822`), una sola volta per Message-ID, massimo 2 MB. Il mittente
  di un'email può essere falsificato: per questo contano comunque solo gli URL dei portali e i
  valori scritti. Un'email malformata è registrata come non leggibile e non blocca le successive;
- gli annunci sono salvati sulla stessa fonte di Vedra Capture per quel dominio: quando poi
  qualcuno invia la pagina di dettaglio, la riga si completa invece di duplicarsi e lo storico
  delle osservazioni resta. Una scheda non sovrascrive mai con valori vuoti dati più ricchi;
  un prezzo diverso è una nuova osservazione. Finché manca il dettaglio l'immobile è
  "Da completare" e non conta come verifica della pagina (`listing_checks` invariato).

Da confermare con un avviso reale inoltrato: il dominio mittente effettivo, il formato dei link
di tracciamento (se la destinazione non è scritta nel link, la scheda viene saltata e contata),
la struttura della scheda e le diciture di ribasso. Le fixture in `backend/tests/fixtures/portal_alerts`
sono sintetiche.

## Navigazione affidata a Hermes

Prova browser del 22 settembre 2026: Chromium avviato sulla VPS con AppArmor
in `enforce`. Immobiliare.it, idealista e Casa.it mostrano inizialmente una
schermata di verifica JavaScript con la allowlist limitata al portale. Su
Immobiliare.it, consentendo lo script pubblico richiesto dalla pagina
(`ct.captcha-delivery.com`) e il dominio dell'iframe osservato
(`geo.captcha-delivery.com`), il sito risponde "Access is temporarily restricted"
e segnala attività insolita dalla rete. Non offre una verifica interattiva o un
login. Nessun CAPTCHA è stato completato; nessun catalogo dei tre portali è stato
verificato. Per idealista e Casa.it resta soltanto la prova con allowlist minima:
non attribuire alla sola rete del portale ciò che dipende dal filtro locale.

Il codice ora espone `browse_source`: Hermes può aprire il catalogo configurato
e seguirne la paginazione verificata. Il browser usa rete nativa con DNS fissato
all'IP pubblico verificato e contesti isolati. Non sono implementati login,
riuso di account, compilazione form o filtri interattivi. L'installazione e il
collaudo sul runtime Hermes devono essere verificati separatamente dai test locali.

Una pagina di login, un CAPTCHA o un errore non sono un catalogo vuoto.
Il nuovo strumento non rimuove le restrizioni dei portali osservate sopra.

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

## ABE Immobiliare

`examples/abe-milano.source.json` configura il catalogo pubblico e i dettagli di
vendita con navigazione browser. Comune e zona sono letti dall'intestazione
esplicita; stato e dati economici dalla tabella della fonte. Il permesso è
spento nell'esempio: l'operatore deve verificare lo scopo d'uso. Non rappresenta
un accordo di licenza dell'agenzia. Le immagini conservano attribuzione e URL;
nessun contenuto degli annunci è incluso nel repository.

I due esempi ricontrollano i dettagli ogni sei ore. I record con comune, prezzo
oppure superficie assenti rientrano comunque nella coda di verifica di Hermes,
anche prima della scadenza, entro il limite per fonte. Gli annunci chiusi restano
esclusi. Una modifica all'estrattore non modifica i record: sarà la successiva
acquisizione dalla fonte a completarli.
