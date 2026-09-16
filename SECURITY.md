# Sicurezza e limiti del modello di fiducia

Vedra 0.3 è un workspace operativo a istanza dedicata, non una piattaforma certificata multi-tenant.

## Controlli presenti

Sessioni HttpOnly/SameSite Strict, CSRF sulle scritture, hash PBKDF2-SHA256 con salt e 600.000 iterazioni, rate limit login locale, ruoli lato server, body massimo 5 MB anche per richieste chunked, CSP senza script inline, nessun rendering del testo degli annunci come HTML attivo. Le fotografie registrate negli annunci sono servite solo dal proxy autenticato su host esplicitamente autorizzati; raster limitati e cache privata, nessun URL arbitrario.

La raccolta HTTP usa allowlist esatta, convalida DNS/IP, connessione all’IP controllato e redirect limitati. Le restrizioni sono applicate anche alle richieste del browser opzionale. Un blocco non viene aggirato. Gli snapshot sono scaricabili soltanto dopo il login e come testo allegato. Gli export neutralizzano formule fornite come testo dall’esterno.

Il gateway Hermes usa una chiave separata. Il bridge macchina espone solo raccolta della run, lettura dei task, invio di classificazioni, chiusura ed enqueue vincolato. Prezzi e calcoli non sono scrivibili dal modello attraverso il bridge. I segreti non arrivano alla dashboard.

## Cosa non garantiscono questi controlli

Una skill non è un confine di sicurezza. Il configuratore ora limita il profilo Hermes ai tre tool MCP di classificazione; il backend verifica il toolset effettivo prima della run. La capability breve viene validata per run, scadenza e stato ed è revocata alla chiusura. Questo non certifica la sandbox del runtime né sostituisce un ambiente isolato. Usare profilo **e ambiente di esecuzione** dedicati, senza home personale, SSH, email o socket privilegiati. Le quote testuali validano la provenienza, non l’interpretazione o la verità dell’annuncio.

Il token legacy di amministrazione del bridge autorizza operazioni nel workspace e non viene trasmesso al modello. Non costituisce isolamento tra tenant. Gli amministratori possono aggiungere utenti e fonti, importare testo e vedere il dataset. Un admin malintenzionato o la compromissione dell’host sono fuori dal perimetro dei controlli applicativi.

Non sono inclusi SSO/MFA, recupero password remoto, rotazione automatica chiavi, audit legale, pen test, rate limiting distribuito, retention, cifratura applicativa del database o sandbox verificata del browser. Non presentare il repository come “GDPR compliant” automaticamente. La configurazione reale, i dati trattati e i contratti devono essere valutati separatamente.

## Segnalazioni

Comunica eventuali problemi privatamente al proprietario del repository, senza pubblicare dati cliente, token, snapshot reali o exploit contro fonti terze. Il repository non contiene un indirizzo di security inventato; definiscilo prima di aprire un canale pubblico di segnalazione.

## Provider diretto e distribuzione

Il modello diretto non ha tool: restituisce il contratto di classificazione e non esegue comandi. Il testo viene validato contro evidenze immutabili ma richiede revisione semantica umana. Endpoint AI, chiavi e SMTP sono configurazione server; mai impostati dai listing. Le chiavi non sono nel browser né nei report. I limiti di run/token non sono un tetto di spesa finanziario: configurarlo anche dal provider.

Inter è richiesto via Google Fonts a runtime con fallback locale. Per una distribuzione senza richieste esterne dal browser rimuovere i link fonts da frontend/index.html; nessun binario font è incluso. La configurazione CSP ammette soltanto quei domini per font/CSS e risorse same-origin per il resto.

## Database cloud e processi

Il ruolo PostgreSQL è dedicato a uno schema privato, non esposto dalla Data API
Supabase. Non usare `postgres` o una service-role key per servire il browser.
Verifica i privilegi effettivi del ruolo nel deployment, TLS, backup cifrati e
permessi del volume. Il frontend Vercel non include `.env`, backend o fixture.
Il reverse proxy blocca `/bridge`; il traffico MCP resta sulla rete privata.

Un advisory lock di sessione esclude il secondo worker PostgreSQL. Questo richiede
connessione diretta o pooler di sessione, non di transazione. Le versioni del
provider, il deployment e il suo pooler non sono stati collaudati qui. Il supporto
DB non equivale a RLS multi-tenant. Il rate limit login è per processo: mantieni
un solo processo API o aggiungi un limite al proxy prima di scalare.
