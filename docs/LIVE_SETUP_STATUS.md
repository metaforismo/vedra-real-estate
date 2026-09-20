# Verifiche della ricerca guidata da Hermes

Revisione applicativa verificata: `137be7c`.

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
