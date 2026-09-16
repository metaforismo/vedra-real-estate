# Aggiornare Vedra 0.1 → 0.2

Questo archivio è un repository completo, non una patch da eseguire. Base verificata:
`ce6e3d96161d1800d06d842853f07aaffb52d780`. Nessuna modifica è stata inviata a GitHub.

## Installazione esistente

1. Ferma Vedra e qualunque writer del database. Non sovrapporre due versioni.
2. Con la vecchia installazione e il suo `.env`, esegui
   `python scripts/backup.py --writes-stopped`. Conserva separatamente `.env` come
   segreto. Il backup contiene dati e hash delle password, non va su GitHub.
3. Copia i sorgenti aggiornati. **Non cancellare** `.env`, `data/`, snapshot o
   backup. Non usare `git clean -xfd` e non sostituire tutto il clone con una
   cartella vuota che perda lo stato.
4. Reinstalla `requirements.txt`. Aggiungi nel `.env` solo le variabili nuove
   necessarie, copiandole da `.env.example` senza duplicare le chiavi.
5. Per dati reali scegli `SEED_DEMO=false`. Questo impedisce nuovi seed ma non
   cancella la demo già presente. Scegli il dataset reale nella UI; la preferenza
   salvata dal browser potrebbe ancora essere demo.
6. Avvia una sola istanza. La migrazione v2 espande i runtime degli agenti e
   aggiunge le tabelle operative in transazione. Preserva utenti, sessioni,
   proprietà, osservazioni, note, fonti e ricerche. Interrompe in caso di
   inconsistenza referenziale preesistente. I test coprono l'idempotenza e i
   riferimenti di un database v1 controllato, non una copia dei dati dell'utente.
7. Riapri il browser con un refresh completo. Verifica login, numero record,
   storico prezzi, fonti, note e una singola run manuale prima del timer.

Hermes richiede riconfigurazione: il nuovo adapter non accetta il vecchio profilo
con terminale generale. Segui [HERMES](HERMES.md), backup del profilo incluso.

## Rollback

Non avviare 0.1 sul database migrato: il runtime `llm` e le nuove tabelle non sono
un contratto compatibile verso il basso. Ferma tutto, ripristina **insieme** i
sorgenti 0.1 e il tuo backup v1 su directory vuota, quindi verifica il `.env`.
Il restore di archivi arbitrari non è automatizzato.

## GitHub

Carica i file nascosti necessari (`.github`, `.gitignore`, `.env.example`) ma
mai `.env`, chiavi, `data/`, database, backup o log privati. L'archivio non contiene
`.git`: conserva quello del tuo clone. Registra un commit delle modifiche dopo i
test locali; non è necessario creare una nuova repository.
