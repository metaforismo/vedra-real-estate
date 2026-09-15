# Sicurezza e limiti del modello di fiducia

Vedra 0.1 è una preview privata a workspace singolo, non una piattaforma certificata multi-tenant.

## Controlli presenti

Sessioni HttpOnly/SameSite Strict, CSRF sulle scritture, hash PBKDF2-SHA256 con salt e 600.000 iterazioni, rate limit login locale, ruoli lato server, body massimo 5 MB anche per richieste chunked, CSP senza script inline, nessun rendering del testo degli annunci come HTML attivo. Le immagini esterne non vengono caricate automaticamente.

La raccolta HTTP usa allowlist esatta, convalida DNS/IP, connessione all’IP controllato e redirect limitati. Le restrizioni sono applicate anche alle richieste del browser opzionale. Un blocco non viene aggirato. Gli snapshot sono scaricabili soltanto dopo il login e come testo allegato. Gli export neutralizzano formule fornite come testo dall’esterno.

Il gateway Hermes usa una chiave separata. Il bridge macchina espone solo raccolta della run, lettura dei task, invio di classificazioni, chiusura ed enqueue vincolato. Prezzi e calcoli non sono scrivibili dal modello attraverso il bridge. I segreti non arrivano alla dashboard.

## Cosa non garantiscono questi controlli

Una skill non è un confine di sicurezza. Il runtime Hermes può avere terminale e altri tool: le istruzioni di non usarli impropriamente non ne rimuovono materialmente le capacità. Usare profilo **e ambiente di esecuzione** dedicati, senza home personale, SSH, email o socket privilegiati. Le quote testuali validano la provenienza, non l’interpretazione o la verità dell’annuncio.

Il bridge token autorizza il workflow nell’intero workspace, non costituisce isolamento tra tenant. Gli amministratori possono aggiungere utenti e fonti, importare testo e vedere il dataset. Un admin malintenzionato o la compromissione dell’host sono fuori dal perimetro della preview.

Non sono inclusi SSO/MFA, recupero password remoto, rotazione automatica chiavi, audit legale, pen test, rate limiting distribuito, retention, cifratura applicativa del database o sandbox verificata del browser. Non presentare il repository come “GDPR compliant” automaticamente. La configurazione reale, i dati trattati e i contratti devono essere valutati separatamente.

## Segnalazioni

Comunica eventuali problemi privatamente al proprietario del repository, senza pubblicare dati cliente, token, snapshot reali o exploit contro fonti terze. Il repository non contiene un indirizzo di security inventato; definiscilo prima di aprire un canale pubblico di segnalazione.
