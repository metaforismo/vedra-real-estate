# Avvio privato, URL cliente e operatività

## Scelta più semplice per la preview

Una macchina Linux con Python, una sola istanza Vedra e un Hermes dedicato sullo stesso host. Il browser cliente vede solo Vedra; il gateway Hermes non è pubblico.

Come punto di partenza operativo, non come misura prestazionale: 2 vCPU e 4 GB di RAM per pochi utenti e un job alla volta. Il rendering browser può richiedere più memoria; misurare sul workload effettivo. Non sono stati eseguiti benchmark di capacità o carico. Non serve una GPU locale: il modello è quello configurato nel profilo Hermes, eventualmente remoto.

Avvia la demo localmente prima di installare servizi. La combinazione della dashboard, dei job e dei dati sintetici funziona senza Hermes o provider LLM.

## URL con HTTPS

1. Installa in una directory dedicata, ad esempio `/opt/vedra`, con un utente di servizio senza privilegi.
2. Genera `.env` con `scripts/setup.py` e conserva il file fuori dal repository remoto. Prepara `data/` scrivibile soltanto dall’utente del servizio.
3. Imposta `PUBLIC_ORIGIN=https://preview.tuo-dominio.it`, `ALLOWED_HOSTS=preview.tuo-dominio.it,localhost,127.0.0.1`, `COOKIE_SECURE=true`.
4. Pubblica DNS verso il server e configura il reverse proxy HTTPS. `docs/Caddyfile.example` mostra il routing nativo e blocca il bridge sull’interfaccia pubblica.
5. Mantieni Uvicorn su loopback e il firewall chiuso sulle porte 8000 e 8645 da Internet. Gli utenti arrivano solo su HTTPS.
6. Crea gli account cliente in Impostazioni, preferibilmente viewer durante la prima presentazione. Le password provvisorie sono definite da te, non incluse nel codice.

`docs/vedra.service.example` è un esempio systemd da adattare ai percorsi reali. Esegui una sola istanza: **non aumentare `--workers`**. Il codice non implementa elezione del worker o una coda distribuita.

Non è stato effettuato un deployment pubblico per questa consegna e non è stato registrato un dominio. Prima di condividere l’URL verifica login, logout, cookie Secure, blocco del bridge pubblico, snapshot, export e una run reale sul server scelto.

## Docker

`docker compose up --build -d` usa il Dockerfile non-root, filesystem applicativo read-only e volume persistente `vedra-data`. `.env` è letto da Compose ma non copiato nell’immagine. Porta host legata a loopback, capability Linux rimosse, nessun socket Docker montato.

Per includere Playwright:

```bash
WITH_BROWSER=1 VEDRA_MEMORY_LIMIT=2g docker compose build
# Imposta anche BROWSER_ENABLED=true nel .env.
VEDRA_MEMORY_LIMIT=2g docker compose up -d
```

L’immagine contiene già i moduli richiesti dagli export; Word/Excel non sono installati e non servono per generarli. Le formule XLSX sono preservate e accompagnate da cache calcolate.

Non è incluso un container Hermes con credenziali preconfezionate. Leggere la sezione rete in HERMES.md: un indirizzo loopback dentro Docker non raggiunge automaticamente Hermes sull’host. Prima della produzione fissare digest delle immagini e verificare le dipendenze; i tag del Dockerfile sono un punto di partenza, non una distinta certificata. Docker build/Compose e il browser containerizzato non sono stati eseguiti qui.

## Dati e account

`ADMIN_PASSWORD` crea soltanto il primo account. Non cambia la password di utenti già presenti al riavvio. Recupero locale:

```bash
python scripts/reset_password.py admin@vedra.local
```

Lo script chiede la nuova password senza stamparla e revoca le sessioni dell’utente. I tre ruoli sono di workspace: tutti gli utenti autorizzati possono vedere tutti i dati di quel workspace; non sono tenant isolati.

In assenza di password configurata al primo avvio, il backend ne genera una e scrive `data/bootstrap-password.txt` con permessi restrittivi. Il percorso raccomandato è `scripts/setup.py`, per avere credenziali esplicite prima dell’avvio. Non consegnare lo stesso account amministratore a tutti.

## Backup

Per il backup offline incluso, ferma app e altri writer:

```bash
python scripts/backup.py --writes-stopped
```

Il tar contiene una copia SQLite consistente e gli snapshot. Non contiene `.env`, che va salvato separatamente come segreto. Il backup contiene comunque dati privati e hash delle password: conservalo cifrato e non su GitHub. Per ripristinare, a servizio fermo estrai un **tuo** backup fidato in una directory vuota e configura `DATA_DIR` su quel percorso. Non estrarre archivi di terzi come root.

Il volume di snapshot/eventi non ha una retention automatica. Pianifica pulizia e cancellazione compatibili con i diritti dei dati prima di monitorare per mesi. È sconsigliato abilitare la scansione continua durante lo sviluppo dei selettori.

## Checklist prima dell’accesso esterno

- HTTPS e allowlist host corretti; nessuna password predefinita condivisa.
- Provider/gateway isolato, budget impostato, terminale privo di segreti personali.
- Fonte approvata e verificata, nessun tentativo di bypass dei blocchi.
- Demo e dati reali separati; benchmark compatibili e con periodo corretto.
- Backup e ripristino provati; spazio disco e log monitorati.
- Test sul browser dei destinatari; note del cliente e dati personali non esposti a utenti estranei.

Questa checklist non è una certificazione di sicurezza, privacy o conformità. La revisione della configurazione effettiva resta necessaria.
