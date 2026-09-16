# Componenti di terze parti

Il pacchetto distribuisce il sorgente di Vedra, non gli ambienti Python, Chromium, Hermes o altri eseguibili. Le dipendenze si installano dagli indici ufficiali attraverso i file requirements.

| Dipendenza diretta | Versione verificata | Licenza dichiarata nei metadata installati |
|---|---|---|
| FastAPI | 0.128.2 | MIT |
| Uvicorn | 0.48.0 | BSD-3-Clause |
| Pydantic | 2.13.4 | MIT |
| HTTPX | 0.28.1 | BSD-3-Clause |
| Beautiful Soup | 4.14.3 | MIT |
| python-docx | 1.2.0 | MIT |
| openpyxl | 3.1.5 | MIT |
| Playwright, opzionale | 1.57.0 | Apache-2.0 |
| pytest, sviluppo | 9.0.2 | MIT |

Le dipendenze transitive mantengono le proprie licenze. Prima di una distribuzione binaria/container al cliente genera un inventario dal relativo ambiente e conserva i testi di licenza richiesti. Le versioni dirette runtime sono fissate; questo non è un lockfile completo delle dipendenze transitive né una attestazione di sicurezza.

## Hermes

Hermes si installa separatamente dal progetto ufficiale NousResearch. L'adattatore usa il protocollo documentato; il codice del runtime Hermes non è copiato nel repository. Non è stato imposto un commit non verificato. Esegui la verifica delle capabilities sul gateway effettivamente installato prima di abilitare il runtime.

## Asset

La dashboard richiede Inter via CSS Google Fonts a runtime, con fallback di sistema offline. Nessun binario di font, fotografia immobiliare o immagine di terzi è incluso. Icone, marchio provvisorio Vedra, illustrazioni CSS e diagrammi dell'interfaccia sono parte del sorgente di questo progetto. Gli screenshot documentano esecuzioni dell'app su dati sintetici, non immobili reali.

## Dati

Tutte le fixture distribuite sono sintetiche. I documenti privati del brief e le conversazioni del cliente non fanno parte del pacchetto. Per dati importati o acquisiti successivamente verifica separatamente accesso, licenze, riuso, conservazione e obblighi verso gli interessati.

PyYAML è una dipendenza opzionale del solo configuratore Hermes, non del server Vedra. La mappa è uno schema disegnato nel codice, non un dataset catastale o una base cartografica di terzi.
