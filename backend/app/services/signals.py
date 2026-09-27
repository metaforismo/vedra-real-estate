"""Compact decision signals shared by lists, daily work and exports."""
import re
from datetime import datetime,timezone

from .decision_facts import contact_route,price_reductions,published_date,text_facts


CONDITIONS=(('to_renovate','Da ristrutturare'),('renovated','Ristrutturato'),('new','Nuovo'))


def _listed(p,instant):
    evidence=p.get('evidence') or {};facts=evidence.get('decision_facts') or {}
    published=facts.get('published_at') if isinstance(facts,dict) else None
    value=published_date(published)
    basis='published' if value else 'first_seen'
    value=value or p.get('first_seen')
    if not value:return None,None,None
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo is None:parsed=parsed.replace(tzinfo=timezone.utc)
        parsed=parsed.astimezone(timezone.utc)
        if parsed>instant:return None,None,None
    except (TypeError,ValueError):return None,None,None
    return max(0,int((instant-parsed).total_seconds()//86400)),parsed.date().isoformat(),basis


def _omi(p,price_sqm):
    context=p.get('market_context') or {}
    rows=context.get('rows') or []
    if context.get('status')!='available' or not rows:return None
    condition=p.get('condition')
    def matches(item):
        value=str(item.get('condition','')).casefold()
        if condition=='to_renovate':return 'scadent' in value or 'da ristrutturare' in value
        if condition=='renovated':return 'ottim' in value or ('ristrutturat' in value and 'da ristrutturare' not in value)
        if condition=='new':return 'nuov' in value
        return False
    row=next((item for item in rows if matches(item)),rows[0])
    try:
        low=float(row['min_sqm']);high=float(row['max_sqm']);mid=round((low+high)/2,2)
    except (KeyError,TypeError,ValueError):return None
    stale=bool(context.get('stale'))
    delta=round((price_sqm/mid-1)*100,1) if price_sqm is not None and mid and not stale else None
    return {'min_sqm':low,'max_sqm':high,'mid_sqm':mid,'delta_pct':delta,'period':context.get('period'),
            'area_basis':row.get('area_basis'),'stale':stale}


def attach_signals(db,items:list[dict],*,references=None,observations=None)->list[dict]:
    if not items:return items
    instant=datetime.now(timezone.utc);observations=dict(observations or {})
    missing=[p['id'] for p in items if p['id'] not in observations and 'observations' not in p]
    for start in range(0,len(missing),400):
        batch=tuple(missing[start:start+400]);marks=','.join('?' for _ in batch)
        for row in db.all('''SELECT o.property_id,o.observed_at,o.price,c.currency,c.transaction_type
            FROM observations o LEFT JOIN observation_context c ON c.observation_id=o.id
            WHERE o.property_id IN ('''+marks+') ORDER BY o.observed_at,o.id',batch):
            observations.setdefault(row['property_id'],[]).append(row)
    shared=references
    for p in items:
        rows=observations.get(p['id'],p.get('observations',[]))
        market=p.get('market_references')
        if market is None:
            if shared is None:
                from .market_references import MarketReferences
                shared=MarketReferences(db)
            market=shared.for_property(p)
        days,since,basis=_listed(p,instant)
        evidence=p.get('evidence') or {};declared=evidence.get('decision_facts') or {}
        if not isinstance(declared,dict):declared={}
        facts={**text_facts(p.get('title',''),p.get('description','')),**declared}
        contact=facts.get('contact') or {}
        if not isinstance(contact,dict):contact={}
        phone=contact.get('telephone');email=contact.get('email')
        route=contact_route(p);price_sqm=p.get('price_sqm')
        refs=[]
        groups={group['key']:group for group in market.get('groups',[])}
        for key,label in CONDITIONS:
            group=groups.get(key,{})
            median=group.get('median_sqm')
            refs.append({'key':key,'label':label,'median_sqm':median,'q1_sqm':group.get('q1_sqm'),
                'q3_sqm':group.get('q3_sqm'),'count':group.get('count',0),'source_count':group.get('source_count',0),
                'delta_pct':round((price_sqm/median-1)*100,1) if price_sqm is not None and median else None,
                'reason':group.get('reason','Servono almeno 3 asset confrontabili')})
        p['signals']={'days_listed':days,'listed_since':since,'listed_basis':basis,
            'reductions':price_reductions(rows,p.get('price'),p.get('currency'),p.get('transaction_type')),
            'cadastral':facts.get('cadastral',{}).get('quote') if isinstance(facts.get('cadastral'),dict) else None,
            'change_of_use':facts.get('change_of_use',{}).get('quote') if isinstance(facts.get('change_of_use'),dict) else None,
            'contact':{'name':contact.get('name') or contact.get('organization') or None,
                'has_phone':bool(isinstance(phone,str) and re.fullmatch(r'\+?\d{6,16}',re.sub(r'[\s().-]','',phone))),
                'has_email':bool(isinstance(email,str) and re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+',email)),
                'route':route['kind'],'route_label':route['label']},
            'market':{'price_sqm':price_sqm,'currency':p.get('currency') if p.get('currency') not in (None,'XXX') else None,
                'refs':refs,'same_condition_key':p.get('condition') if p.get('condition') in dict(CONDITIONS) else None,
                'omi':_omi(p,price_sqm)}}
    return items
