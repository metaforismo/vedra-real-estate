# Costi di esercizio di Scout

Stima basata sulle prove dal vivo del 27 e 28 settembre 2026 con Regolo `qwen3.8-27b`
(€ 0,50 per milione di token in ingresso, € 2,10 in uscita, ragionamento `low`).
Vedra gira in locale: nessun costo di hosting.

## Misurato

| Prova | Pagine lette | Schede estratte | Token in / out | Costo |
|---|---|---|---|---|
| ABE Immobiliare, pagina annunci | 1 | 5 | 8.557 / 5.860 | € 0,017 |
| Tecnocasa, dalla homepage | 2 | 4 | 20.047 / 7.425 | € 0,026 |
| Tecnocasa + Gabetti + immobiliare.it (bloccato) | 3 | 2 | 41.826 / 4.997 | € 0,031 |
| Studio di accuratezza, 28/9: 25 schede di 7 agenzie | — | 25 | 60.524 / 65.219 | € 0,167 |
| Studio di accuratezza, 28/9: 20 pagine di risultati × 5 istruzioni | 20 | — | 173.389 / 34.966 | € 0,160 |

Ordine di grandezza misurato il 28/9: **€ 0,007–0,008 per pagina di risultati** delle grandi reti
(100–220 link per pagina: Tecnocasa, RE/MAX, Engel & Völkers, dove.it) e **€ 0,0067 per scheda nuova**
(in media 2.400 token in ingresso e 2.600 in uscita, quasi tutti di ragionamento). La stima di
€ 0,002 per pagina del 27/9 valeva per pagine piccole come quella di ABE.
Un annuncio già acquisito e recente non viene riletto: una ricerca periodica senza novità
costa soltanto la lettura delle pagine di risultati.

## Scenario tipo

7 fonti, ricerca ogni 6 ore (4 al giorno), 2 pagine di risultati per fonte, 30 annunci nuovi
al giorno:

| Voce | Calcolo | Al mese |
|---|---|---|
| Lettura pagine | 7 × 4 × 2 × € 0,008 × 30 | ≈ € 13,4 |
| Schede nuove | 30 × € 0,0067 × 30 | ≈ € 6,0 |
| Sintesi e criteri personalizzati | 30 × € 0,003 × 30 | ≈ € 2,7 |
| **Totale modello** | | **≈ € 22** |

Il costo reale di ogni esecuzione è nel riepilogo della ricerca (pagine aperte, letture AI,
euro stimati) e cresce con la frequenza, il numero di fonti e le istruzioni più lunghe.
Ogni 15 minuti invece che ogni 6 ore moltiplica la voce “lettura pagine” per 24.
Partire dalla pagina di risultati della città (non dalla homepage) evita una lettura per fonte.

## Tempi del servizio AI

Il 28/9 pomeriggio Regolo ha rallentato a circa 28 token al secondo: una lettura di pagina (fino a
~2.000 token di ragionamento, 4.000 al massimo) richiede allora 1–2 minuti. Per questo le chiamate di
Scout hanno un limite proprio, `AI_SCOUT_TIMEOUT_SECONDS` (predefinito 240 s), separato da
`AI_TIMEOUT_SECONDS` delle chiamate brevi; nessuna chiamata va oltre la scadenza della ricerca
(`RUN_TIMEOUT_SECONDS`, predefinito 900 s, di cui l’ultimo 20% fino a 3 minuti è riservato alle sintesi).
Quando il servizio è lento la ricerca termina come **parziale** e lo dice: pagine e schede non lette,
nessun annuncio scartato per questo. Il costo delle chiamate interrotte non viene riportato dal
fornitore e non compare nel riepilogo.

## Cosa non è incluso

- Il tempo del team per verificare contatti e documenti.
- Portali che bloccano l’accesso automatico (immobiliare.it, idealista, casa.it): nessun costo
  perché non vengono letti; per coprirli servono canali autorizzati (feed o accordi).
- Eventuale server cloud, se in futuro si sceglie di non usare i PC locali.
