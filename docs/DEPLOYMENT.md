# Deployment

Per **Vercel + Supabase + VPS** segui [CLOUD.md](CLOUD.md). Vercel ospita il frontend,
Supabase lo schema privato PostgreSQL, la VPS API, collector/worker e Hermes
opzionale. Non far girare un browser persistente o uno scheduler infinito in una
Function Vercel. Le azioni lunghe accodano una run e tornano subito un identificatore.

Per l'installazione locale o su un solo server usa `start.sh` o `compose.yaml`:
SQLite, volume `data/` persistente e un solo processo Vedra. Il runtime AI è
opzionale. Non serve una GPU locale per un provider remoto.

Esempi supportati in `deploy/`:
- `Caddyfile.example`: TLS/reverse proxy, bridge Hermes non esposto.
- `vedra-api.service.example` e `vedra-worker.service.example`: processi systemd
  separati, utente senza privilegi e `.env` privato.
- `supabase.sql`: ruolo dedicato e schema non pubblico.

Non avviare contemporaneamente `compose.yaml` e `compose.cloud.yaml` sullo stesso
workspace. Non raddoppiare i worker Uvicorn nel deployment SQLite. Le protezioni
di lock impediscono un secondo worker, ma non trasformano il prodotto in una coda
multi-worker distribuita. Il database cloud deve usare una sessione persistente
(diretto o pool sessione), non il pool transazione sulla porta 6543.

Nessun deployment pubblico, load test o SLA è stato verificato in questa consegna.
Usa il collaudo `LOCAL_TEST.md` su una fonte reale prima della consegna al cliente.
