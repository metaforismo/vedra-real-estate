# Distribuzione per cliente e percorso SaaS

## Implementato

L'unità d'isolamento è **un'installazione dedicata**: database/schema e ruolo,
volume privato, segreti, API, worker e profilo Hermes separati per cliente.
`WORKSPACE_ID` è identificazione, non autorizzazione multi-tenant. Gli utenti di
un'istanza vedono il relativo workspace secondo i ruoli admin/analyst/viewer.

Sono presenti pipeline, scenari, inbox, fonti, benchmark, audit, ricerche persistenti,
provider configurabili, client PostgreSQL/Supabase e build frontend Vercel. Il
browser non riceve la password del DB o una service-role key. L'accesso è attraverso
l'API Vedra; non si dichiara RLS multi-tenant come già implementata.

## Non ancora implementato

Billing/abbonamenti, self-signup, SSO/MFA, inviti monouso, provisioning self-service,
quote commerciali, coda distribuita e isolamento di più aziende nello stesso
schema condiviso. Supabase Auth/Storage non sono usati: le sessioni sono gestite da
Vedra e gli snapshot nel volume privato VPS. PostGIS e geocoding automatico non
sono implementati.

Prima di vendere un SaaS self-service condiviso serve una fase dedicata: tenancy,
policy verificabili su query/export/worker, ruoli e inviti, misurazione e limiti,
conservazione e cancellazione dati, ripristino da backup e sicurezza del deployment.
Separare i moduli oggi evita di legare quei lavori a uno specifico provider AI;
non significa che tutti quei requisiti siano già completati.
