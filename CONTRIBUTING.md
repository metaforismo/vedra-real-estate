# Contribuire

La prima release è una preview a workspace singolo. Prima di estenderla leggi
[architettura](docs/ARCHITECTURE.md), [contratto dati](docs/DATA.md) e
[limiti verificati](TEST_REPORT.md).

1. Crea un branch per un cambiamento circoscritto.
2. Scrivi fixture sintetiche per il caso; non inserire credenziali o annunci raccolti da terzi.
3. Aggiungi test del percorso normale, del dato mancante e del fallimento della fonte.
4. Esegui `pytest -q`, `node scripts/check_frontend.mjs`, `python scripts/test_ui.py`.
5. Per modifiche alla UI allega screenshot desktop/mobile con badge DEMO.
6. Aggiorna documentazione e CHANGELOG senza trasformare funzionalità previste in capacità già presenti.

Non rimuovere controlli di rete, tracciabilità o separazione dei dataset per far passare una demo.
Non introdurre nuove dipendenze o un fork di Hermes senza una motivazione misurabile.
