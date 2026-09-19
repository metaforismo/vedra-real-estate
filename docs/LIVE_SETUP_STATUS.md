# Verifica live del 19 settembre 2026

Frontend: https://vedra-real-estate-indol.vercel.app
API HTTPS: https://vedra-api.92.4.222.134.sslip.io
Codice: branch `codex/live-setup`, PR #1.

## Installazione attiva

- Vercel: frontend statico e proxy API nella stessa origine; deployment
  `dpl_E62tJQEN4F9Jcm2fniQPaEKMaveo`, stato READY.
- Oracle: servizi `vedra-api`, `vedra-worker`, `vedra-hermes`, `caddy`.
- PostgreSQL 16: database e ruolo dedicati `vedra`, schema `vedra`, socket locale.
  Supabase non creato: quota gratuita esaurita; nessun piano a pagamento attivato.
- Hermes 0.20.5 dedicato in `/opt/vedra-hermes`, profilo
  `/var/lib/vedra/.hermes/profiles/vedra`, API privata su 127.0.0.1:8645.
  Hermes personale non modificato. Patch di enumerazione MCP descritta in HERMES.md.
- Regolo: endpoint `/v1`, modello `qwen3.8-27b`, provider custom, reasoning xhigh.
- `/bridge` escluso sia dal proxy Vercel sia da Caddy. API e database non espongono
  direttamente le porte interne. HTTPS usa un hostname sslip.io: per un servizio
  stabile è opportuno sostituirlo con un dominio controllato dal progetto.

## Dati e prova reale

Ricerca manuale «Milano · Appartamenti 500–600k», residenziale in vendita,
500.000–600.000 EUR inclusivi, nessuna asta, nessun minimo di superficie.
Due schede con fatti essenziali rilevati da pagine pubbliche il 19/09/2026:
Rembrandt (500.000 EUR, 86 m²) e Porta Venezia (550.000 EUR, 55 m²).
Ogni scheda conserva URL della fonte e nota di rilevazione manuale.
Nessuna foto o descrizione integrale ripubblicata. Disponibilità da confermare
con l'agenzia. Dati esterni e credenziali sono esclusi da Git e ZIP.

Run Vedra `f148eb98-74f5-4672-891f-a947e3e21329`: **completed**,
2 elaborati, 2 compatibili, 0 errori, `analysis_done=1`.
Run Hermes `run_002540531ab148b385e9430a3255c4d9`: classificazione reale con
Regolo; entrambe le analisi sono state validate dal backend e salvate in PostgreSQL.

Questa prova dimostra hosting, persistenza e analisi AI reali. I dati iniziali sono
una ricognizione manuale: non è attivo un crawler periodico dei portali.
Le condizioni PropertyRE limitano il riuso delle schede; per la raccolta ricorrente
serve una fonte/feed con autorizzazione compatibile. Non sono presenti benchmark
inventati, valutazioni di mercato o rendimenti presunti.

## Verifiche

| Controllo | Esito |
| --- | --- |
| pytest locale | 305 PASS, 4 PostgreSQL skip locali |
| PostgreSQL su database separato `vedra_validation` | 4 PASS |
| Sintassi JS / mappa / catalogo | 14 moduli / 8 invarianti / 7 test PASS |
| API e worker in processi separati | 7 controlli PASS |
| UI locale | 18 scenari PASS desktop/mobile e tema scuro |
| Login HTTPS tramite Vercel | PASS |
| Workspace, catalogo, insights, readiness live | HTTP 200 |
| Verifica strumenti Hermes live | Esattamente i tre tool MCP Vedra |
| Run reale Hermes/Regolo | completed, 2 analisi validate |
| Bridge da Internet tramite Vercel | HTTP 404 |

La UI locale usa fixture temporanee: le immagini di quei test non sono prove
degli immobili reali. La pagina di login pubblica è stata verificata nel browser;
le API autenticate e la run reale sono state verificate sul deployment pubblico.
Un warning Starlette/AnyIO non bloccante rimane nelle suite Python.

## Gestione

Le credenziali amministratore sono consegnate in un file locale privato, non nella
PR. Il server conserva l'ambiente in `/opt/vedra/.env` (0600).
Riavvio: `sudo systemctl restart vedra-api vedra-worker vedra-hermes`.
Configurazione proxy: `/etc/caddy/Caddyfile`.
Per aggiornare il frontend usare `VEDRA_API_ORIGIN` e `scripts/build_vercel.py`,
poi una versione recente di Vercel CLI con `deploy --prebuilt --prod`.
Rivedere la patch Hermes quando si aggiorna il runtime dedicato.
