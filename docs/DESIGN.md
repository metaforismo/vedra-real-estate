# Design engineering

Riferimento richiesto: `emilkowalski/skills`, skill `emil-design-eng`, revisione
`85e8e2363b713506e1d5b6e07a0eb2da66be1bc3` (MIT). I principi sono applicati alla UI,
non usati come istruzioni per accedere ai dati del cliente.

| Prima | Dopo | Motivo |
|---|---|---|
| Selettore demo/reale | Un solo workspace reale con onboarding | Nessuna ambiguità nei numeri mostrati al cliente. |
| Illustrazioni di immobili | Foto dell’annuncio consentite oppure placeholder esplicito | Non attribuire foto fittizie all’asset. |
| Panoramiche duplicate | `overview.js` con primitive in `ui.js` | Un punto di manutenzione per heading, metriche e miniature. |
| Stato worker in memoria API | Heartbeat condiviso persistente | La UI rileva anche il worker su processo distinto. |
| Indicatori senza contesto | Metodo, finestra, numerosità e dati mancanti | Un numero non supportato viene omesso. |
| Cambio vista che perde il focus | Ripristino del focus e selezione dell’input | Uso continuo da tastiera senza interruzioni. |

Inter configurato via CSS con fallback di sistema. Non distribuire file di font.
Palette blu/navy, contrasto e gerarchia del contenuto; successo/errore usano colori
semantici separati. Niente avatar di agenti, rendimenti, grafici o foto fittizi.

Le animazioni devono giustificarsi: transizioni brevi su proprietà esplicite, feedback
pressione e `prefers-reduced-motion`. Non animare conteggi come se fossero metriche
live quando non c’è una nuova osservazione. Le azioni da tastiera sono immediate.

Prima di una PR UI: controllare mobile, focus, stato vuoto, errore, caricamento,
contenuto lungo e dati incompleti. Non aggiungere librerie solo per un componente
che esiste già. Screenshot di collaudo popolati con fixture vanno marcati nel report;
le immagini pubblicate della release mostrano lo stato vuoto reale.

Fonte: https://github.com/emilkowalski/skills/tree/85e8e2363b713506e1d5b6e07a0eb2da66be1bc3

## Archivio 0.4

| Prima | Dopo | Motivo |
|---|---|---|
| Filtri sul campione in memoria | Catalogo server-side con conteggio e pagine | Il cliente trova anche i record più vecchi. |
| Selezione limitata alla pagina | Selezione fino a 100 ID tra pagine, confermata dal server | Il lavoro di revisione non viene perso cambiando pagina. |
| Salvataggi uno a uno | Dialogo di revisione multipla con riepilogo e nota | Controllo umano prima della mutazione; nessuna sovrascrittura dei ruoli/checklist. |
| Risposta di ricerca obsoleta | AbortController, generazioni di richiesta e debounce | I risultati vecchi non rimpiazzano quelli appena richiesti. |
| Focus perso durante un filtro | ID stabili e ripristino del focus su input/select | La navigazione da tastiera rimane prevedibile. |
| Numero senza provenienza storica | Timeline dei soli valori conservati e contesto valutario | Si distingue una variazione osservata da una supposizione. |

CSS dedicato `catalog.css`, primitive condivise di `ui.js`, azioni separate dalle viste.
Nessuna nuova dipendenza UI. Tabella e schede offrono la stessa selezione, il limite
è visibile. Gli errori sostituiscono le righe stale e conservano i filtri per correggerli.
