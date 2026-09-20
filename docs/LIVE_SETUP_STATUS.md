# Verifiche della ricerca guidata da Hermes

Revisione applicativa verificata: `b68882c`; correzione setup `bdc9d29`.

## Flusso end-to-end

Due esecuzioni avviate dalla dashboard e completate dal runtime remoto reale:

| Controllo | Prima esecuzione | Seconda esecuzione |
| --- | --- | --- |
| Link trovati nella fonte configurata | 20 | 20 |
| Annunci acquisiti dalla fonte | 3 | 3 |
| Nuovi record | 3 | 0 |
| Modifiche rilevate | 0 | 0 |
| Compatibili con i criteri | 2 | 2 |
| Errori | 0 | 0 |

Gli eventi documentano ricerca e acquisizione richieste da Hermes, seguite da
persistenza, analisi e completamento. Un annuncio resta escluso perché manca il
campo città. La seconda lettura mantiene gli stessi identificativi senza duplicati.
Non essendoci variazioni reali del prezzo fra le due letture, il collaudo live non
prova un cambio di prezzo; lo storico delle modifiche è verificato dai test.

La ricerca copre una fonte HTML configurata, non l'intero mercato. L'aggiornamento
giornaliero è configurato con prossima esecuzione salvata; la futura esecuzione
programmata non è ancora osservata. Foto e benchmark non disponibili restano tali.

## Correzioni emerse nel collaudo

- Query della dashboard non compatibile con PostgreSQL: corretto l'alias SQL e
  aggiunta copertura all'integrazione PostgreSQL.
- Contatore acquisiti aggiornato soltanto a raccolta conclusa: ora ogni acquisizione
  aggiorna i contatori persistenti anche durante la run.

## Controlli

- 309 test Python locali passati; 4 test PostgreSQL passati su database separato.
- 14 moduli JavaScript, 8 controlli mappa, 7 test catalogo, 7 controlli processi
  e 18 scenari UI locali passati. Le fixture restano limitate al collaudo.
- Live: accesso, dashboard, avvio ricerca, log, fonti, filtro agente, filtro criteri,
  vista schede, dettaglio con analisi/provenienza e salvataggio della frequenza.
- Mobile: navigazione, log e scheda immobile a 393 px, senza overflow orizzontale.
- Esportazioni CSV/Excel: due risultati corrispondenti al filtro dei criteri.
- Endpoint autenticati di workspace, operations, catalogo, insight, readiness,
  notifiche, agenti e fonti: HTTP 200. Bridge pubblico: HTTP 404.

Questi controlli verificano i percorsi descritti, non garantiscono assenza di ogni bug.
URL privati, indirizzi delle VM, account, credenziali e identificativi operativi
sono conservati fuori dal repository e dalla descrizione della PR.

## Ricerca locale e aggiornamento dell'estrattore

Il modulo agente salva una dicitura di zona o indirizzo, mostrata anche nella
scheda agente. Hermes riceve contesto testuale dei candidati, prezzi indicativi e
criteri; il backend verifica i dettagli e applica il filtro ai campi di posizione.
Gli stati espliciti ristrutturato/ottime condizioni sono normalizzati conservando
il testo originale. Negazioni e condizioni ambigue rimangono sconosciute.

Verifiche aggiuntive: 326 test Python passati, 4 PostgreSQL su database temporaneo,
14 moduli JS, 8 controlli mappa, 7 test catalogo, 7 controlli processi e 18 scenari UI.
Il campo locale è stato verificato anche nel salvataggio UI e a 393 px senza
overflow. Un problema emerso nel setup privilegiato è stato corretto: il file
privato mantiene il proprietario del servizio dopo la sostituzione atomica.
Sei test setup passano; la conservazione dell'owner è verificata anche su Linux
con un file temporaneo appartenente a un utente differente.

Per funzionalità operative e lacune del confronto economico, vedi
[Flusso di ricerca e limiti dei dati](PRODUCT_READINESS.md).

Collaudo live della ricerca locale, avviata e configurata dalla dashboard:
20 link scoperti, un annuncio selezionato e acquisito da Hermes, un record
aggiornato, zero nuovi duplicati, zero errori e un risultato compatibile.
La classificazione Hermes è stata validata e la run è terminata `completed`.
La scheda mostra stato normalizzato buono, completezza 80%, due osservazioni con
versione dell'estrattore e prezzo invariato. Restano esplicitamente mancanti
micro-zona e base della superficie; sconto e score economico sono non disponibili.
