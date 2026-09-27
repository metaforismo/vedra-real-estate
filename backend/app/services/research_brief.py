"""User-defined research scope, resolved in code before opening a source."""
import hashlib
from urllib.parse import quote, urlsplit
from ..db import dump,load


def catalog_url(agent,source):
    return agent['criteria'].get('source_urls',{}).get(source['id']) or load(source['config'])['search_url'].replace('{city}',quote(agent['city'].lower().replace(' ','-'),safe=''))


def validate_targets(criteria,sources):
    selected={s['id']:s for s in sources if s}
    for ident,url in criteria.source_urls.items():
        source=selected.get(ident)
        if not source or source['kind']!='html':raise ValueError('La pagina personalizzata richiede una fonte web selezionata.')
        try:
            p=urlsplit(url)
            valid=p.scheme in ('http','https') and p.hostname==source['domain'] and p.port in (None,80,443) and not p.username and not p.password
        except ValueError:valid=False
        if not valid or '\\' in url or any(ord(c)<32 for c in url):raise ValueError('La pagina deve usare il dominio della fonte, senza credenziali né porte personalizzate.')


def brief(agent,sources):
    criteria=agent['criteria']
    data={'instructions':criteria.get('research_instructions',''), 'selection_criteria':criteria.get('custom_prompt',''),
          'contact_policy':criteria.get('contact_policy','any'),
          'opportunity_only':criteria.get('opportunity_only',False),
          'min_discount':criteria.get('min_discount'),
          'contact_task':'Cerca la pubblicazione originale e il recapito del proprietario o agente con mandato nelle sole fonti consentite. Acquisisci la pagina che documenta il ruolo. Non inferire mandato dal nome o dal numero di telefono; conserva i casi incerti.',
          'targets':[{'source_id':s['id'],'name':s['name'],'url':catalog_url(agent,s)} for s in sources]}
    return data|{'version':hashlib.sha256(dump(data).encode()).hexdigest()[:16]}


def deliver(db,rid,agent,sources):
    data=brief(agent,sources)
    if not db.one("SELECT id FROM events WHERE run_id=? AND step='research_brief'",(rid,)):
        db.event(rid,'research_brief','Istruzioni e pagine di ricerca consegnate a Hermes.',data=data)
    return data
