# Collaudo locale con dati reali

L'obiettivo è verificare il percorso sorgente→annunci→seconda run→analisi→dashboard,
non soltanto che si apra una schermata. Nessuna prova qui richiede di caricare
segreti nella repo. Partire da una sola fonte autorizzata e pochi annunci.

## 1. Avvio vuoto e account

Avvia normalmente: il dataset operativo è sempre reale e vuoto. Il database vuoto non è un errore:
Panoramica, mappa, comparabili e inbox devono indicarlo senza numeri inventati.
Verifica impostazioni, un secondo utente viewer e i permessi di scrittura.

## 2. Acquisizione reale

Configura il dominio esatto in `LIVE_ALLOWED_DOMAINS`, riavvia e crea la fonte.
Annota permesso, URL, selettori, massimo pagine e refresh dettagli. Prova la fonte
nella dashboard. Controlla manualmente prezzo, valuta, superficie, base superficie,
comune, tipo, stato e descrizione di almeno cinque annunci.

Non basta trovare cinque link. Quando compaiono dati ignoti, rimangono ignoti;
non riempirli con supposizioni per ottenere uno score. Un blocco del sito va
registrato, non aggirato. La fonte con status errore non equivale a zero opportunità.

## 3. Due esecuzioni e ripartenza

Crea un agente Regole locali, manuale, max 5 annunci. Esegui una run e annota ID,
record, snapshot ed eventi. Ripeti: non devono apparire copie dello stesso
`source+listing_key`. I dettagli nel periodo di cache non vengono riletti e non
acquistano una falsa data di osservazione recente. Il contatore delle richieste
pagina non include tutti i byte/robots/asset del browser.

Il controllo periodico delle ricerche e il refresh dettagli hanno frequenze
distinte. Un ribasso non notificato dalla sorgente verrà visto soltanto quando il
dettaglio sarà nuovamente letto. L'assenza da una scansione parziale non marca un
immobile come venduto o rimosso.

Riavvia dopo una run completata. Ripeti senza duplicazioni. Interrompere una run
in corso deve farla risultare interrotta al riavvio; non promettiamo la ripresa
esatta di ogni step remoto. Ripetila manualmente con lo stesso criterio.

## 4. AI facoltativa

Configura un provider come in [AI](AI.md). Regolo/Qwen è soltanto l'esempio locale.
`check_ai.py` senza flag non fa rete. `--live --accept-cost` prova un solo testo
sintetico e può addebitare token. Con test riuscito, crea una ricerca `AI configurata`
sulla fonte reale e controlla citazioni, strategie e caveat. Una seconda run
invariata non deve spendere token per gli stessi annunci già analizzati.

Prova anche credenziale non valida, modello non disponibile o budget ridotto:
il sistema deve segnalarlo, non presentare le regole come risposta AI. Dopo la
prova elimina il segreto sbagliato. Non salvare errori con credenziali su GitHub.

## 5. Valore per il cliente

Porta un immobile in shortlist/due diligence, assegna responsabile e scadenza.
Apri la stessa revisione in due tab: il salvataggio vecchio deve ricevere conflitto.
Aggiungi una nota. Calcola e salva uno scenario con ipotesi definite dal cliente;
riaprilo e verifica aritmetica e sensibilità. I comparabili devono rimanere
indisponibili quando mancano omogeneità o campione minimo. Controlla export e fonti.

## 6. Monitoraggio per alcune ore

Abilita il timer (minimo 15 minuti) solo dopo le verifiche. Controlla Stato operativo,
run fallite/parziali, cache, errori fonte, spazio disco e consumi provider. Metti in
pausa: non devono partire nuovi job pianificati. Uno già in corso va annullato
separatamente. Configura SMTP soltanto quando serve; consegna at-least-once, quindi
una rara email duplicata è possibile dopo un crash nel punto invio/conferma DB.

## Esito da registrare

Documenta fonte/data/criteri, record davvero acquisiti, campi utili, valori mancanti,
ritardo osservato, falsi duplicati, citazioni errate, token addebitati e comportamento
al riavvio. Non sostituire queste misure con le percentuali degli screenshot.
Il report incluso riguarda test controllati; questa è la verifica del tuo ambiente.

## 8. Separazione API/worker e messa in produzione

Arresta il worker: l'API deve continuare a funzionare, la diagnostica deve indicare
worker non disponibile e la coda non deve risultare falsamente completata. Riavvia
il worker e verifica consumo della coda, idempotenza e log. Una seconda istanza
deve essere rifiutata. Esegui un backup e una prova di ripristino in una base
separata. Per la validazione interna offline: `scripts/test_worker_processes.py`.

Per Vercel/Supabase valida nel tuo deployment cookie Secure, CSRF/origin, TLS,
rewrite senza cache, connessione in modalità sessione, permessi del ruolo e
esclusione dello schema privato da PostgREST. Non limitarti al rendering della UI.
