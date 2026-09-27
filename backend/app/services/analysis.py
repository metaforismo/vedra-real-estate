from __future__ import annotations

import hashlib
import re
import math
from datetime import datetime, timezone

from ..schemas import Criteria, SemanticAnalysis

QUALITY_FIELDS=['price','surface','title','description','city','zone','address','property_type','condition','area_basis']


def completeness(p: dict) -> tuple[float,list[str]]:
    present=[k for k in QUALITY_FIELDS if p.get(k) not in (None,'','unknown',[],{})]
    return round(len(present)/len(QUALITY_FIELDS)*100),[k for k in QUALITY_FIELDS if k not in present]


RULES={
    'value_add': [r'\bda ristrutturare\b',r'\bfrazionabile\b',r'\briqualificazione\b',r'\bfrazionamento\b'],
    'core_plus': [r'\ba reddito\b',r'\battualmente locato\b',r'\bimmobile locato\b'],
    'development': [r'\bterreno edificabile\b',r'\bdemolizione e ricostruzione\b'],
    'conversion': [r'\bpossibile cambio d.?uso\b',r'\bpossibilità di cambio d.?uso\b',r'\bcambio di destinazione\b'],
}


def classify_rules(p: dict) -> dict:
    text=(p.get('title','')+'. '+p.get('description','')).strip()
    strategies=[]
    for strategy,patterns in RULES.items():
        for pattern in patterns:
            match=re.search(pattern,text,re.I)
            if not match:
                continue
            before=text[max(0,match.start()-45):match.start()].lower()
            if re.search(r'\b(non|vietat[oa]|esclus[oa]|nessun[oa]?)\b',before):
                continue
            quote=text[max(0,match.start()-25):min(len(text),match.end()+85)].strip()
            strategies.append({'strategy':strategy,'evidence':quote})
            break
    caveats=['Classificazione a regole, non una valutazione AI. Le strategie sono ipotesi di screening.']
    if any(x['strategy']=='conversion' for x in strategies):
        caveats.append('Il cambio d’uso è soltanto dichiarato nell’annuncio: fattibilità urbanistica non verificata.')
    if p.get('is_auction'):
        caveats.append('Perizia, occupazione, abusi e costi della procedura richiedono verifica professionale.')
    return {'engine':'rules','summary':text[:400], 'strategies':strategies,'caveats':caveats,'version':'strategy-rules/1.0'}


def prompt_key(prompt: str) -> str:
    return hashlib.sha256('\n'.join(' '.join(line.split()) for line in prompt.strip().splitlines() if line.strip()).encode()).hexdigest()


def custom_assessment(p: dict, prompt: str) -> dict | None:
    item=p.get('analysis',{}).get('custom_assessments',{}).get(prompt_key(prompt))
    return item if item and item.get('content_hash')==p.get('content_hash') else None


def validate_semantic(p: dict, raw: dict) -> dict:
    validated=SemanticAnalysis.model_validate(raw).model_dump()
    source=' '.join((p.get('title','')+' '+p.get('description','')).split()).casefold()
    seen=set()
    for item in validated['strategies']:
        evidence=' '.join(item['evidence'].split()).casefold()
        if evidence not in source:
            raise ValueError('La citazione non compare nel titolo o nella descrizione acquisita.')
        if item['strategy'] in seen:
            raise ValueError('Strategia duplicata.')
        seen.add(item['strategy'])
    source+=' '+' '.join(p.get('source_context','').split()).casefold()
    assessment=validated.pop('custom_assessment',None)
    prompt=p.get('custom_prompt','')
    if prompt:
        if assessment is None:
            raise ValueError('Manca la verifica dei criteri personalizzati.')
        for quote in assessment['evidence']:
            if ' '.join(quote.split()).casefold() not in source:
                raise ValueError('Citazione qualitativa assente dalla fonte.')
        if assessment['status']!='uncertain' and not assessment['evidence']:
            raise ValueError('Un esito qualitativo definitivo richiede evidenze.')
        requirements=[line.strip() for line in prompt.splitlines() if line.strip()]
        checks=assessment.get('checks',[])
        if checks or len(requirements)>1:
            supplied={}
            for check in checks:
                criterion=check['criterion']
                if criterion not in requirements or criterion in supplied:raise ValueError('Criterio estraneo o duplicato.')
                for quote in check['evidence']:
                    if not 5<=len(quote.strip())<=700 or ' '.join(quote.split()).casefold() not in source:raise ValueError('Citazione del criterio assente dalla fonte.')
                if check['status']!='uncertain' and not check['evidence']:raise ValueError('Ogni criterio definitivo richiede una citazione.')
                supplied[criterion]=check
            assessment['checks']=[supplied.get(line,{'criterion':line,'status':'uncertain','reason':'Criterio non verificato nella risposta AI.','evidence':[]}) for line in requirements]
            states={check['status'] for check in assessment['checks']}
            assessment['status']='not_matched' if 'not_matched' in states else 'uncertain' if 'uncertain' in states else 'matched'
            if len(supplied)<len(requirements):assessment['reason']='Uno o più criteri non sono stati verificati.'
        if p.get('description_truncated') and assessment['status']!='uncertain':
            assessment['status']='uncertain'
            assessment['reason']='Descrizione parziale: verifica i criteri sul testo completo. '+assessment['reason'][:720]
        validated['custom_assessments']={prompt_key(prompt):{
            **assessment,'prompt':prompt,'content_hash':p.get('content_hash')}}
    elif assessment is not None:
        raise ValueError('Verifica qualitativa non richiesta per questo task.')
    validated['engine']='hermes'
    validated['version']='semantic-contract/1.0'
    validated['caveats']=validated['caveats'][:7]+['Ipotesi AI da verificare. Nessuna certificazione urbanistica o indicazione di rendimento.']
    return validated


def match_benchmark(p: dict, benchmarks: list[dict]) -> tuple[dict | None,str]:
    keys=('city','zone','property_type','condition','area_basis','currency','transaction_type')
    if any(not p.get(k) or p[k]=='unknown' for k in keys):
        return None,'Micro-zona, tipologia, stato o base di superficie insufficienti per un confronto omogeneo.'
    matches=[b for b in benchmarks if bool(b['is_demo'])==bool(p.get('is_demo')) and all(str(b.get(k,'')).casefold()==str(p.get(k,'')).casefold() for k in keys)]
    if not matches:
        return None,'Nessun benchmark compatibile. Non usiamo una media generica di città come sostituto.'
    b=max(matches,key=lambda v:v['period'])
    year=int(b['period'][:4]); half=int(b['period'][-1])
    current=datetime.now(timezone.utc)
    months=(current.year-year)*12+current.month-(6 if half==1 else 12)
    if (year,half) > (current.year,1 if current.month<=6 else 2):
        return None,'Benchmark di un periodo futuro: verifica la data della fonte.'
    if months>18:
        return None,'Benchmark oltre 18 mesi: aggiornalo prima del confronto.'
    return b,''


def opportunity(p: dict, benchmark: dict | None, analysis: dict) -> tuple[float | None,float | None,list[dict]]:
    if p.get('availability') in ('sold','rented','withdrawn'):return None,None,[]
    if not benchmark or not p.get('price') or not p.get('surface'):
        return None,None,[]
    midpoint=(benchmark['min_sqm']+benchmark['max_sqm'])/2
    price_sqm=p['price']/p['surface']
    discount=(1-price_sqm/midpoint)*100
    if not math.isfinite(discount):return None,None,[]
    price_points=max(0,min(70,35+discount*1.4))
    strategy_points=min(30,15*len(analysis.get('strategies',[])))
    details=[{'label':'Prezzo rispetto al punto medio del range','points':round(price_points,1),'max':70,
              'formula':'clamp(35 + sconto_percentuale × 1,4; 0; 70)'},
             {'label':'Strategie con evidenza testuale','points':strategy_points,'max':30,
              'formula':'min(30; 15 × numero_strategie_con_evidenza)'}]
    return round(price_points+strategy_points),round(discount,2),details


def screen(p: dict, agent: dict) -> tuple[bool,list[str]]:
    criteria=agent['criteria'] if isinstance(agent['criteria'],dict) else {}
    c=Criteria.model_validate(criteria)
    reasons=[]
    if c.custom_prompt:
        assessment=custom_assessment(p,c.custom_prompt)
        if not assessment: reasons.append('Criteri personalizzati: verifica AI da eseguire')
        elif assessment['status']!='matched': reasons.append(('Criteri personalizzati non soddisfatti: ' if assessment['status']=='not_matched' else 'Criteri personalizzati da verificare: ')+assessment['reason'])
    if p.get('availability') in ('sold','rented','withdrawn','review'):reasons.append('Annuncio non più attivo')
    if p.get('city','').casefold()!=agent['city'].casefold(): reasons.append('Comune diverso dalla ricerca')
    if c.location_query:
        # Match the stated location, not nearby amenities in marketing descriptions.
        tokens=re.findall(r'\w+',c.location_query.casefold())
        pattern=r'(?<!\w)'+r'[\W_]+'.join(re.escape(t) for t in tokens)+r'(?!\w)'
        if not tokens or not any(re.search(pattern,str(p.get(k) or '').casefold()) for k in ('zone','address','title')):
            reasons.append('Zona o indirizzo richiesto non documentato nell’annuncio')
    if p.get('transaction_type')!='sale': reasons.append('Non risulta una compravendita')
    if p.get('currency')!='EUR': reasons.append('Valuta non EUR')
    if p.get('price') is None: reasons.append('Prezzo assente')
    elif p['price']<c.min_price: reasons.append('Prezzo sotto il budget minimo')
    elif p['price']>c.max_price: reasons.append('Prezzo sopra il budget')
    if p.get('surface') is None: reasons.append('Superficie assente')
    else:
        if p['surface']<c.min_surface: reasons.append('Superficie sotto la soglia')
        if c.max_surface and p['surface']>c.max_surface: reasons.append('Superficie sopra la soglia')
    if c.property_types and p.get('property_type') not in c.property_types: reasons.append('Tipologia fuori ricerca')
    if not c.include_auctions and p.get('is_auction'): reasons.append('Aste escluse')
    if c.opportunity_only and (p.get('discount') is None or p['discount']<=0):
        reasons.append('Vantaggio di prezzo non documentato sul benchmark')
    if c.contact_policy=='require_direct':
        from .decision_facts import contact_route
        contact=p.get('evidence',{}).get('decision_facts',{}).get('contact') or {}
        if contact_route(p)['kind']=='unknown' or not (contact.get('telephone') or contact.get('email')):
            reasons.append('Contatto diretto con recapito non documentato')
    if c.min_discount is not None:
        if p.get('discount') is None: reasons.append('Confronto di prezzo non disponibile')
        elif p['discount']<c.min_discount: reasons.append('Sconto inferiore alla soglia')
    strategies={s['strategy'] for s in p.get('analysis',{}).get('strategies',[])}
    if c.strategies and not strategies.intersection(c.strategies): reasons.append('Nessuna strategia richiesta supportata dal testo')
    return not reasons,reasons


def duplicate_candidates(properties: list[dict]) -> list[dict]:
    def norm(s): return re.sub(r'[^\w]','',s.casefold())
    out=[]
    for index,a in enumerate(properties):
        if not a.get('address') or not a.get('surface'): continue
        for b in properties[index+1:]:
            if a['source_id']==b['source_id'] or bool(a['is_demo'])!=bool(b['is_demo']): continue
            if not b.get('surface') or not b.get('address'): continue
            if (norm(a['city'])==norm(b['city']) and norm(a['address'])==norm(b['address']) and a['property_type']==b['property_type'] and abs(a['surface']-b['surface'])/max(a['surface'],b['surface'])<=0.03):
                out.append({'a':a['id'],'b':b['id'],'reason':'Indirizzo e tipologia uguali, superficie entro il 3%. Unità interna non verificata: non uniti automaticamente.'})
    return out
