"""Local configuration checks only: a configured source is not a tested source."""
from datetime import datetime, timezone

from ..db import load
from .worker import worker_health


def check_agent(db, settings, agent: dict) -> dict:
    from ..datasets import legacy_source
    instant = datetime.now(timezone.utc)
    source_ids = load(agent['source_ids'], [])
    checks, sources = [], []
    runtime = agent['runtime']
    online = load(agent['criteria'], {}).get('online_discovery', False)
    configured = runtime == 'local' or (runtime == 'llm' and settings.ai_configured) or (runtime == 'hermes' and bool(settings.hermes_key))
    checks.append({'code':'runtime', 'ok':bool(configured), 'blocking':not configured,
                   'message':('Regole locali: nessuna chiamata AI.' if runtime=='local' else
                              'Runtime configurato. Connessione e qualità del modello non verificate.') if configured
                             else 'Configura le credenziali del runtime sul server.'})
    for sid in source_ids:
        row = db.one('SELECT * FROM sources WHERE id=?', (sid,))
        blockers, warnings = [], []
        if not row or legacy_source(row):
            sources.append({'id':sid, 'name':'Fonte non disponibile', 'ready':False,
                            'blockers':['Fonte assente o non operativa.'], 'warnings':[]})
            continue
        config = load(row['config'], {})
        if not row['enabled']:
            blockers.append('Fonte disabilitata.')
        if row['kind'] == 'html':
            if row['domain'] not in settings.live_domains:
                blockers.append('Dominio non autorizzato sul server.')
            if not row['permission_at'] or not row['permission_note'].strip():
                blockers.append('Permesso della fonte non documentato.')
            if config.get('render_js') and not settings.browser_enabled:
                blockers.append('Questa fonte richiede il browser, disabilitato sul server.')
            health = db.one('SELECT next_retry FROM source_health WHERE source_id=?', (sid,))
            if health and health['next_retry']:
                try:
                    retry = datetime.fromisoformat(health['next_retry'])
                    if retry.tzinfo is None:
                        raise ValueError('timezone missing')
                    if retry > instant:
                        blockers.append('Fonte in attesa dopo un errore. Prossimo tentativo: ' + health['next_retry'])
                except (ValueError, TypeError):
                    blockers.append('Data di riprova non valida. Verifica la configurazione della fonte.')
            probe = db.one('SELECT report FROM source_probes WHERE source_id=?', (sid,))
            if not probe:
                warnings.append('Nessuna verifica di estrazione salvata: esegui Test in Fonti.')
            elif not load(probe['report'], {}).get('ok'):
                warnings.append('L’ultima verifica di estrazione richiede attenzione.')
        else:
            if online:
                blockers.append('La ricerca online Hermes richiede una fonte HTML.')
            count = db.one('SELECT COUNT(*) n FROM properties WHERE source_id=? AND is_demo=0', (sid,))['n']
            warnings.append('Fonte importata: rianalizza l’archivio, non trova nuovi annunci online.')
            if not count:
                blockers.append('Importa almeno un annuncio in questa fonte.')
        sources.append({'id':sid,'name':row['name'],'ready':not blockers,'blockers':blockers,'warnings':warnings})
    available = sum(source['ready'] for source in sources)
    checks.append({'code':'sources','ok':available>0,'blocking':available==0,
                   'message':f'{available} su {len(sources)} fonti utilizzabili con la configurazione corrente.'})
    worker = worker_health(db, settings)
    checks.append({'code':'worker','ok':worker['healthy'],'blocking':False,
                   'message':'Worker rilevato.' if worker['healthy'] else 'Worker non rilevato: la run resterà in coda finché non viene avviato.'})
    scheduled = bool(agent['active'] and agent['interval_minutes'])
    checks.append({'code':'schedule','ok':not scheduled or settings.scheduler,'blocking':False,
                   'message':'Programmazione disponibile.' if not scheduled or settings.scheduler else 'Scheduler disattivato: questa ricerca non partirà automaticamente.'})
    running = db.one("SELECT id,status FROM runs WHERE agent_id=? AND status IN ('queued','running','cancelling')", (agent['id'],))
    can_enqueue = all(not check['blocking'] for check in checks)
    return {'agent_id':agent['id'], 'can_enqueue':can_enqueue, 'can_run_now':can_enqueue and worker['healthy'],
            'checks':checks, 'sources':sources, 'active_run':running, 'computed_at':instant.isoformat(),
            'notice':'Controllo locale di configurazione, senza richieste al portale o al modello. Nessuna garanzia sulla copertura dei dati.'}
