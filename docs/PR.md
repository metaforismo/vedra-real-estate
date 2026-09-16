# Pubblicare la release tramite PR

La consegna contiene sorgenti e patch; non implica una PR remota già aperta o un
merge già effettuato. Nel contesto di sviluppo gli strumenti GitHub erano in sola
lettura e il trasporto Git non raggiungeva github.com. Il helper esegue le scritture
soltanto quando lo lancia l'operatore autenticato con GitHub CLI.

## Percorso raccomandato

Mantieni il clone esistente **pulito**. Non copiarci prima la release: la patch
include aggiunte, modifiche e cancellazioni. Dal pacchetto estratto:

```bash
python scripts/publish_pr.py --repo /percorso/al/clone/vedra-real-estate \
  --patch /percorso/Vedra_0.3.0.patch
```

Il helper verifica la repo e il commit base `6d4325bdfe0431df8b6dc261908cf114d8b8536f`,
crea `release/vedra-0.3.0`, applica la patch con controllo, crea un commit con la
**tua identità Git locale**, pubblica il nuovo branch e apre la PR. Non resetta
branch esistenti né usa force push. Se main è avanzato, si ferma: integra/rebasa e
rivedi le nuove modifiche, senza sovrascriverle.

Aggiungi `--merge` per attendere al massimo 30 minuti e tentare il merge solo quando
**tests e postgres** risultano passati, nessun altro check è pendente/fallito,
nessuna revisione lo impedisce e l'head è ancora il commit appena pubblicato. Usa
squash con `--match-head-commit`, senza `--admin`. In caso di timeout/fallimento la
PR rimane aperta; non dichiara successo e non disattiva branch protection.

Su un repository con ulteriori deployment/check obbligatori attendi anche quelli.
Se usi una merge queue, conferma lo stato finale sul sito; un inserimento in coda
non è un merge completato. Il helper verifica di vedere `MERGED` dopo il comando.

Le prove locali del helper coprono i cancelli di sicurezza; push e merge remoti
non sono stati eseguiti nell'ambiente di consegna.
