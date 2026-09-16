# Vercel, Supabase e VPS

## Contratto di distribuzione

Una istanza dedicata per cliente: frontend statico su Vercel, API FastAPI e un worker
sulla VPS, database nello schema privato `vedra` di PostgreSQL/Supabase. Snapshot e
cache immagini rimangono nel volume `DATA_DIR` della VPS. I processi API e worker
devono condividere questo volume e la configurazione database.

Non mettere il worker in una funzione Vercel: mantiene processi, lock e task lunghi.
Le API di avvio restituiscono un ID; la UI legge stato/eventi senza attendere la
conclusione nel singolo HTTP. Il polling sostituisce SSE quando un proxy interrompe
lo stream. Il limite delle riscritture esterne non diventa un limite della run.

## 1. PostgreSQL privato

Esegui `deploy/supabase.sql` come amministratore del progetto. Imposta una password
per `vedra_app` tramite un canale privato, ad esempio `\password vedra_app` in psql.
Non inserire questa password nello script SQL o nel repository.

Copia la connessione dal pannello Connect, con ruolo `vedra_app`:
- connessione diretta, oppure session pooler (porta 5432);
- per il pooler, il nome utente include il riferimento del progetto, secondo la stringa
  fornita da Supabase;
- **non transaction pooler/porta 6543**: Vedra usa stato di sessione e advisory lock;
- usa TLS. Configurazione consigliata: `sslmode=verify-full` con il certificato CA
  indicato dal provider e `sslrootcert=/percorso/ca.crt`. Non disabilitare TLS remoto.

Non aggiungere `vedra` agli schemi esposti dalla Data API. Il ruolo applicativo deve
poter gestire soltanto questo schema. Le migrazioni creano le tabelle, non il ruolo
privilegiato; il browser non si collega direttamente a Postgres e non riceve una
`service_role` key. Le RLS di un eventuale futuro frontend Supabase non sono il
modello di autorizzazione di questa release.

## 2. Configurazione VPS

Installa il repository, Python 3.11+ e `requirements-cloud.txt`. Esegui setup e modifica
il `.env` generato. Esempio **senza credenziali**:

```dotenv
DATABASE_URL=postgresql://...stringa-privata-fornita-da-Supabase...
DATABASE_SCHEMA=vedra
DATABASE_POOL_SIZE=4
WORKER_ENABLED=false
SCHEDULER_ENABLED=true
PUBLIC_ORIGIN=https://app.tuo-dominio.it
ALLOWED_HOSTS=127.0.0.1,localhost,api.tuo-dominio.it,app.tuo-dominio.it
COOKIE_SECURE=true
LIVE_ALLOWED_DOMAINS=
IMAGE_ALLOWED_DOMAINS=
```

`DATABASE_POOL_SIZE` vale per processo: API e worker aprono pool distinti. Il worker
occupa una connessione dedicata per il lock. Parti con un solo processo API e un solo
worker; non scalare orizzontalmente a caso.

Per un primo avvio, in due terminali sulla VPS:

```bash
python scripts/run.py --host 127.0.0.1 --port 8000
python scripts/worker.py
```

Per processi persistenti usa gli esempi systemd in `deploy/`. In alternativa:

```bash
docker compose -f compose.cloud.yaml up --build -d
```

I container condividono un volume e il database. Il cloud compose installa il driver
PostgreSQL; `WITH_BROWSER=1` aggiunge Chromium quando realmente necessario. Non
pubblicare la porta del worker. Il backend HTTP è esposto solo su loopback.

Configura HTTPS con `deploy/Caddyfile.example`. Il reverse proxy pubblico **blocca
`/bridge`**; Hermes sulla stessa VPS può raggiungerlo dalla loopback privata. Non
esporre pubblicamente il gateway Hermes.

## 3. Frontend Vercel

Importa la repo in Vercel, root del progetto = radice della repo. Nessun framework.
Aggiungi soltanto questa variabile build:

```dotenv
VEDRA_API_ORIGIN=https://api.tuo-dominio.it
```

`vercel.json` lancia `python3 scripts/build_vercel.py`. Il risultato Build Output v3
contiene solo HTML, CSS, JS e asset pubblici. `/api/*` viene inoltrato all’API via HTTPS;
`/bridge/*` è negato. Le risposte API non vengono messe in cache.

Il login è quello Vedra, via cookie HTTP-only same-origin e CSRF. Non serve CORS
permissivo. `PUBLIC_ORIGIN` sulla VPS deve corrispondere al dominio frontend definitivo:
le preview Vercel con nomi casuali non sono automaticamente autorizzate alle scritture.
Non aggiungere wildcard per risolvere un errore di origine.

## 4. Fonti, foto e AI

`LIVE_ALLOWED_DOMAINS` abilita soltanto host esatti per i connettori. Il test e il
collector mantengono robots, limiti e pause. `IMAGE_ALLOWED_DOMAINS` abilita separatamente
le foto effettivamente associate agli annunci; senza questo elenco la UI mostra
«Foto non disponibile». Le immagini sono raster limitati in dimensione, con cache
locale limitata; non c’è una foto stock sostitutiva.

Per Hermes su processi nativi della stessa VPS, usa `scripts/configure_hermes.py`
e [HERMES.md](HERMES.md). Con Docker, `127.0.0.1` nel container non è la loopback
host: usa un servizio Hermes sulla rete privata o esegui API/worker nativamente.
Non rendere pubblico Hermes per superare questa differenza di rete.

## 5. Collaudo prima di invitare il cliente

Verifica login HTTPS, mutazioni CSRF, refresh sessione, un’importazione reale del cliente,
poi una fonte autorizzata. Crea una ricerca, eseguila due volte e controlla ID/storico.
Ferma e riavvia il worker: la UI deve segnalare l’assenza senza perdere dati; nessun
secondo worker deve partire sullo stesso database. Valida il primo risultato AI con
le evidenze. Non promettere accesso ai portali finché il loro connettore non è verificato.

## Backup e limiti

Per PostgreSQL usa `pg_dump` con credenziali gestite fuori dalla shell history e salva
anche il volume snapshot. Lo script `backup.py` è solo SQLite e rifiuta un target
PostgreSQL. Prova il ripristino in un ambiente separato. I file possono contenere
contenuti privati e hash password: cifrali e non caricarli su GitHub.

Hosting, SSL reale, Supabase, Docker e provider non vengono dichiarati collaudati
senza una prova sul deployment. Consulta il rapporto di release.

Fonti tecniche consultate:
- https://supabase.com/docs/guides/database/connecting-to-postgres
- https://supabase.com/docs/guides/self-hosting/accessing-postgres
- https://vercel.com/docs/build-output-api
- https://vercel.com/docs/routing/rewrites
