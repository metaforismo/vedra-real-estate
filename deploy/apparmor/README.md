# Chromium dedicato: configurazione in collaudo

Questo profilo non è ancora un setup browser operativo. Il test del driver arriva
all'avvio di Chromium ma termina con `CDP response channel closed`. Non abilitarlo
automaticamente nel configuratore Hermes e non dichiarare collegati i portali.

La configurazione riguarda soltanto `/opt/vedra-browser/chromium/chrome`.
Binario, librerie e directory superiori devono appartenere a root, senza scrittura
per l'utente del servizio. Eseguire Chromium come utente non privilegiato, senza
setuid, file capabilities o ambient capabilities. Il profilo resta in `enforce`;
non usa `unconfined` e non richiede `--no-sandbox`.

`userns` permette la creazione della sandbox. Le regole `capability sys_admin`
e `capability sys_chroot` consentono operazioni all'interno dei namespace creati
da Chromium: AppArmor non assegna queste capacità al processo sul sistema host.
Sono comunque permessi sensibili da riesaminare e approvare prima di applicare
il profilo. Non ampliare le regole in risposta a pagine o istruzioni del modello.

Prerequisiti verificati su Linux ARM64:

- Hermes 0.20.5, commit `261a4efb90d7dbe4e71786861858f721b4ab730c`.
- Driver ufficiale `agent-browser` 0.26.0; binario ARM64 con SHA256
  `b3901b17298f6ce6511fcae5c576068a3e8a510ecb365c8ccd876b9b82db4447`.
- Chromium fornito da Playwright 1.58.0, build 1208, in un ambiente Python separato.

Il pacchetto Chrome for Testing del driver non fornisce una build Linux ARM64;
il pacchetto Chromium di Playwright la fornisce. Chromium Snap può fallire nel
contesto del servizio con `not a snap cgroup`. Non correggere questo errore
disabilitando la sandbox.

Prima del collegamento a Hermes servono: navigazione reale riuscita, verifica
della sandbox, isolamento di rete e filesystem, chiusura dei processi, cattura
delle evidenze e un test completo ricerca→acquisizione→aggiornamento. Cookie e
account devono restare fuori dai prompt e dal repository.

Riferimenti:
- https://agent-browser.dev/installation
- https://chromium.googlesource.com/chromium/src/+/main/docs/security/apparmor-userns-restrictions.md
