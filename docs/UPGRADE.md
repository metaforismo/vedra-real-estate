# Aggiornare da 0.2.0 a 0.3.0

La base del lavoro è `6d4325bdfe0431df8b6dc261908cf114d8b8536f`. Prima di applicare
patch o ZIP confronta le eventuali modifiche successive della tua repo; non cancellare
`.git`, `.env`, `data/` o i backup. Il metodo preferito è una PR con il diff revisionato.

## SQLite esistente

1. Ferma API e worker e fai `python scripts/backup.py --writes-stopped` con la configurazione
   SQLite precedente. Conserva anche `.env` privatamente.
2. Aggiorna i file sorgenti e le dipendenze. I file rimossi dal nuovo repository non
   vengono cancellati da una semplice copia di ZIP: usa la patch o rimuovi quelli elencati
   dal diff, in particolare `backend/app/services/seed.py` e i cataloghi in
   `frontend/public/examples/*-demo.*`.
3. Rimuovi `SEED_DEMO` da `.env`. La 0.3.0 lo ignora comunque. Il nuovo default è sempre
   dati reali; non esiste un endpoint per ricaricare la demo.
4. Avvia una sola istanza. La migrazione v3 aggiunge contesto storico, heartbeat e prove
   delle fonti. Le vecchie osservazioni non ricevono un contesto inventato a posteriori.
5. Ispeziona con `python scripts/purge_demo.py`. Per eliminare i record legacy, ferma
   nuovamente le scritture, assicurati che la coda sia vuota e usa:

```bash
python scripts/purge_demo.py --apply --writes-stopped --backup-confirmed
```

La pulizia è transazionale e conservativa. Rimuove record marcati sintetici e le loro
relazioni; mantiene i dati reali, gli account e le decisioni relative ai dati reali.
Gli agenti con fonti miste perdono la fonte demo e rimangono in pausa. Backup e file
snapshot sul disco vengono conservati: non sono esposti dal frontend.

## SQLite → Supabase/PostgreSQL

Provisiona prima uno schema **vuoto** secondo CLOUD.md e configura `DATABASE_URL` nel
nuovo ambiente. Non avviare ancora API/worker sul target, perché il bootstrap crea un
utente e la migrazione rifiuta giustamente un target popolato.

```bash
python scripts/migrate_sqlite.py --source /percorso/vecchio/vedra.sqlite3
python scripts/migrate_sqlite.py --source /percorso/vecchio/vedra.sqlite3 --apply --writes-stopped
```

La lettura usa un backup SQLite temporaneo coerente; il file originale non cambia.
La copia elimina i dati legacy nella sola copia, conserva ID/relazioni e trasferisce
le tabelle in una transazione. Il target deve essere vuoto. Le sessioni e le capability
Hermes non vengono trasferite. Copia separatamente `snapshots/` nel volume VPS,
quindi avvia API e worker. La password degli utenti trasferiti non è sostituita da
`ADMIN_PASSWORD`: usa quelle esistenti o la procedura di reset.

Se la copia fallisce non cancellare il sorgente; ripristina o correggi il target e
ripeti i test. Non esiste rollback automatico da PostgreSQL a SQLite.

## Verifica del pacchetto

Il manifest SHA256 nello ZIP copre i file sorgenti, escluso il manifest stesso.
Puoi verificarlo dalla radice estratta con `sha256sum -c MANIFEST.sha256` su Linux o
uno script hashlib. Non ricalcolarlo prima della verifica.
