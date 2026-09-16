# Presentazione e prova cliente: distinguere fixture e dati reali

## Prima dell’incontro

Avvia il workspace, crea gli account viewer, prova login/logout, una run manuale e almeno un export. Per la parte dati prepara un piccolo campione ottenuto legittimamente dalla fonte effettiva e segna quali dati mancano. Non usare una fixture sintetica come evidenza della riuscita dello scraping.

## 1. Mostrare il prodotto

Apri Panoramica con il badge **Dimostrativo** visibile. Spiega che questi dati servono a mostrare l’esperienza, non a provare la disponibilità di un portale. Mostra navigazione, risultati, agente e qualità.

## 2. Configurare una ricerca

Agenti → Nuovo agente. Comune Milano, budget e superficie scelti dal cliente, catalogo demo Milano, frequenza Manuale. Premi Esegui ora. Il log mostra una pipeline reale su fixture, senza spese LLM. Apri i risultati dell’agente e il filtro Nei criteri.

## 3. Una scheda verificabile

Apri un immobile: prezzo, superficie, delta, formula score, strategie e citazioni. Mostra anche un caso senza prezzo o senza benchmark. Se il riferimento manca, “non disponibile” è il risultato corretto; non una UI incompleta da nascondere.

Modifica lo stato a In valutazione, scrivi una nota e confronta due immobili. Scarica una scheda Word o l’Excel.

## 4. La vera domanda: i dati bastano?

Passa a **Dati reali**. Mostra il campione realmente ottenuto o importa un file legittimo del cliente. Apri Fonte → Test e i log solo se è stato predisposto e autorizzato l’accesso. Se il portale blocca la richiesta, mostra il blocco e la necessità di cambiare modalità di acquisizione, non una finta scansione positiva.

Qualità dati risponde a: quanti record abbiamo acquisito nel campione? Quali campi sono presenti? Dove mancano indirizzo esatto, micro-zona, stato, superficie confrontabile o dati per una strategia? Il confronto prezzi esiste soltanto se il benchmark è importato e compatibile.

## 5. AI e prossima decisione

Se provider e modello sono stati provati sul server, scegli AI configurata oppure Hermes per una ricerca piccola e mostra una classificazione reale con il relativo log. In caso contrario dichiara che il runtime locale sta usando regole deterministiche e mostra l’integrazione come presente nel codice ma ancora da collaudare con quelle credenziali.

Chiedi al cliente di decidere sul campione: quali campi sono indispensabili? Quale fonte manca? Quali dati possono confermare loro? Quale numero di falsi positivi è tollerabile? Non chiedere di approvare un algoritmo soltanto perché assegna 91/100.

## Cosa non promettere

Nessuna copertura completa dei portali, precisione urbanistica, opportunità sicuramente profittevole, immobile già acquistabile o costo di dati a zero per sempre. L’esito utile è concordare se il campione senza API basta per proseguire e quali verifiche devono entrare nel contratto successivo.

Per il collaudo operativo usa [LOCAL_TEST](LOCAL_TEST.md); per partire senza fixture lascia SEED_DEMO=false. La demo grafica non è il criterio di accettazione dei dati.
