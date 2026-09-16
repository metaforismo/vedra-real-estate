# Architettura 0.2

```text
Browser cliente → API Vedra → SQLite e job persistenti
                               ↓
                    un worker, un processo
                               ↓
         collector HTML/JSON-LD/CSS/sitemap o import
                               ↓
               validazione → storico → screening
                               ↓
        regole | Chat Completions | Hermes/MCP ristretto
                               ↓
          evidenze validate → formule → dashboard
                               ↓
                  inbox e outbox SMTP opzionale
```

Il clock appartiene a Vedra, non al modello. Configurazione dell'agente fotografata
all'accodamento, run e task associati a revisioni immutabili. Un indice univoco
impedisce due run attive dello stesso agente. Un lock OS impedisce due processi
con lo stesso database; non offre distribuzione fra host. Un riavvio marca le run
attive interrotte e invalida le capability Hermes, senza fingere completamento.

`migrations.py` applica lo schema 2 prima di avviare worker; tutte le nuove tabelle
operative sono additive, il CHECK dei runtime è espanso in transazione. Fare un
backup prima di aggiornare.

Il collector fa rete con allowlist, robots e limiti. La cache dei dettagli è distinta
dallo storico: un risultato in cache non attesta una visita recente. Zero link
è un errore di acquisizione da investigare; non cancelliamo annunci assenti da
scansioni parziali. Gli snapshot non sono privati input nascosti per altri clienti.

Il runtime diretto invia solo i campi semantici del task. Hermes riceve una
capability breve e tre strumenti MCP. Prezzo, benchmark e score non sono scrivibili
attraverso il contratto AI. Le citazioni esistenti non sono una prova automatica
della correttezza di ogni inferenza: manteniamo revisione umana e caveat.

Scenari economici sono funzioni deterministiche su ipotesi esplicite. Comparabili
interni sono prezzi richiesti, campione omogeneo min3, non transazioni o perizie.
La revisione dei duplicati non elimina evidenze. Le fasi di pipeline sono decisioni
umane, non certificazioni AI. La checklist usa versione per optimistic concurrency.

Email in outbox separata dal collector: tentativi limitati, dati sintetici esclusi,
consegna at-least-once, Message-ID stabile. A crash fra invio e salvataggio può
seguire un duplicato; non dichiariamo exactly-once.

Per crescere, mantenere i contratti e sostituire storage/queue attraverso migrazioni
verificate, non riscrivere in parallelo un runtime generalista. Vedi [SAAS](SAAS.md).
