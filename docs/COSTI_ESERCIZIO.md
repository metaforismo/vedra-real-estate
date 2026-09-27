# Costi di esercizio di Scout

Stima basata sulle prove dal vivo del 27 settembre 2026 con Regolo `qwen3.8-27b`
(€ 0,50 per milione di token in ingresso, € 2,10 in uscita, ragionamento `low`).
Vedra gira in locale: nessun costo di hosting.

## Misurato

| Prova | Pagine lette | Schede estratte | Token in / out | Costo |
|---|---|---|---|---|
| ABE Immobiliare, pagina annunci | 1 | 5 | 8.557 / 5.860 | € 0,017 |
| Tecnocasa, dalla homepage | 2 | 4 | 20.047 / 7.425 | € 0,026 |
| Tecnocasa + Gabetti + immobiliare.it (bloccato) | 3 | 2 | 41.826 / 4.997 | € 0,031 |

Ordine di grandezza: **€ 0,002 per pagina di risultati** e **€ 0,004–0,006 per scheda nuova**.
Un annuncio già acquisito e recente non viene riletto: una ricerca periodica senza novità
costa soltanto la lettura delle pagine di risultati.

## Scenario tipo

7 fonti, ricerca ogni 6 ore (4 al giorno), 2 pagine di risultati per fonte, 30 annunci nuovi
al giorno:

| Voce | Calcolo | Al mese |
|---|---|---|
| Lettura pagine | 7 × 4 × 2 × € 0,002 × 30 | ≈ € 3,4 |
| Schede nuove | 30 × € 0,006 × 30 | ≈ € 5,4 |
| Sintesi e criteri personalizzati | 30 × € 0,003 × 30 | ≈ € 2,7 |
| **Totale modello** | | **≈ € 12** |

Il costo reale di ogni esecuzione è nel riepilogo della ricerca (pagine aperte, letture AI,
euro stimati) e cresce con la frequenza, il numero di fonti e le istruzioni più lunghe.
Ogni 15 minuti invece che ogni 6 ore moltiplica la voce “lettura pagine” per 24.

## Cosa non è incluso

- Il tempo del team per verificare contatti e documenti.
- Portali che bloccano l’accesso automatico (immobiliare.it, idealista, casa.it): nessun costo
  perché non vengono letti; per coprirli servono canali autorizzati (feed o accordi).
- Eventuale server cloud, se in futuro si sceglie di non usare i PC locali.
