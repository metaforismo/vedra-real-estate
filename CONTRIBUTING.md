# Contribuire

Leggi `AGENTS.md`, `docs/ARCHITECTURE.md` e `TEST_REPORT.md`. Lavora su una modifica
circoscritta con test dei percorsi normali, campi mancanti, errori e riavvio.

```bash
python -m pip install -r requirements-dev.txt -r requirements-hermes.txt
pytest -q
node scripts/check_frontend.mjs
node scripts/test_map.mjs
python scripts/test_worker_processes.py
python scripts/test_ui.py
```

Per SQL/migrazioni esegui anche `backend/tests/test_postgres.py` con una base
**disponibile e dedicata ai test** in `TEST_DATABASE_URL`: crea e cancella schemi
random propri. Mai puntarlo a un database cliente. La CI prepara PostgreSQL 16.

Dati sintetici solo sotto `backend/tests/`, in database temporanei del collaudo.
Non aggiungere cataloghi o seed al prodotto per abbellire una schermata. Gli stati
vuoti sono componenti del prodotto. Non includere credenziali, file font, HTML
raccolto da terzi o documenti cliente. Non aggirare i controlli di accesso dei siti.

Prima della PR: test verdi, diff leggibile, documentazione dei limiti, screenshot
che dichiarino il contesto della prova. Per questa release vedi `docs/PR.md`.
