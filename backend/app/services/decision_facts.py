"""Decision aids from published declarations, kept separate from human verification."""
import re
from datetime import datetime,timezone


def text_facts(title,description):
    text=title+'\n'+description
    facts={}
    patterns={
        'cadastral':r'(?:categoria\s+catastale|catasto|accatastat[oa]|cat\.)[^.;\n]{0,50}?\b[A-F]\s*/\s*\d{1,2}\b',
        'change_of_use':r'[^.!?\n]{0,90}(?:cambio\s+(?:di\s+)?(?:destinazione(?:\s+d[’\']uso)?|d[’\']uso)|destinabile\s+a\s+residenza)[^.!?\n]{0,170}',
        'mandate':r'[^.!?\n]{0,70}(?:mandato\s+(?:in\s+)?esclusiv[oa]|incarico\s+in\s+esclusiva|vendita\s+diretta\s+(?:dal|da)\s+proprietario)[^.!?\n]{0,100}',
    }
    for key,pattern in patterns.items():
        match=re.search(pattern,text,re.I)
        if match:facts[key]={'quote':match.group().strip(),'status':'dichiarato nella fonte'}
    return facts


def published_date(value):
    if not isinstance(value,str):return None
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo is None:parsed=parsed.replace(tzinfo=timezone.utc)
        if parsed>datetime.now(timezone.utc):return None
        return parsed.isoformat()
    except ValueError:return None


def contact_from_schema(chosen,wrappers,offer,clean):
    # A footer Organization is not necessarily the broker for this asset.
    for node in [offer,chosen,*wrappers]:
        for key in ('seller','offeredBy','broker'):
            item=node.get(key)
            if not isinstance(item,dict):continue
            contact={k:clean(item.get(k,''))[:240] for k in ('name','telephone','email')}
            if isinstance(item.get('worksFor'),dict):contact['organization']=clean(item['worksFor'].get('name',''))[:240]
            if not any(contact.values()):continue
            phone=re.sub(r'[\s().-]','',contact['telephone'])
            contact['telephone']=phone if re.fullmatch(r'\+?\d{6,16}',phone) else ''
            email=contact['email']
            contact['email']=email if re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+',email) else ''
            contact['method']='JSON-LD '+key
            contact['role']='Inserzionista dichiarato'
            return contact
    return None


def price_reductions(observations=(),current_price=None,current_currency=None,current_transaction=None):
    count=0;previous=None;last_at=None
    for item in observations:
        price=item['price']
        context=(item.get('currency'),item.get('transaction_type'))
        comparable=context[0] not in (None,'XXX') and context[1] in ('sale','rent')
        if previous and comparable and price is not None and previous[1]==context and previous[0] is not None and price<previous[0]:
            count+=1
            if item.get('observed_at') and (last_at is None or item['observed_at']>last_at):last_at=item['observed_at']
        previous=(price,context)
    context=(current_currency,current_transaction)
    comparable=context[0] not in (None,'XXX') and context[1] in ('sale','rent')
    prices=[item['price'] for item in observations if comparable and item.get('price') is not None and
            (item.get('currency'),item.get('transaction_type'))==context]
    highest=max(prices) if prices else None
    total=round((current_price/highest-1)*100,1) if current_price is not None and highest and current_price<highest else None
    return {'count':count,'total_pct':total,'from_price':highest if total is not None else None,'last_at':last_at}


def dossier(p,observations=(),calls=()):
    evidence=p.get('evidence',{})
    result={**text_facts(p.get('title',''),p.get('description','')),**evidence.get('decision_facts',{})}
    result['source_url']=p['url'];result['observed_at']=p.get('last_seen')
    result['price_reductions']=price_reductions(observations)['count']
    result['first_seen']=p.get('first_seen')
    result['calls']=list(calls)
    result['contact']=result.get('contact') or None
    result['contact_route']=contact_route(p)
    return result


def source_context(p):
    facts=p.get('evidence',{}).get('decision_facts',{})
    contact=facts.get('contact') or {}
    return '\n'.join(key+': '+str(contact[key]) for key in ('name','organization','telephone','email','role') if contact.get(key))


def contact_route(p):
    """A declaration about this listing is a lead, never a verified mandate."""
    text=p.get('title','')+'\n'+p.get('description','')
    patterns=[('owner_declared','Proprietario dichiarato',r'vendita\s+diretta\s+(?:(?:dal|da)\s+proprietario|da\s+privato)|(?:vendo|vendiamo)\s+da\s+privato'),
              ('mandate_declared','Mandato esclusivo dichiarato',r'mandato\s+(?:in\s+)?esclusiv[oa]|incarico\s+in\s+esclusiva')]
    found=[]
    for kind,label,pattern in patterns:
        for match in re.finditer(pattern,text,re.I):
            before=text[max(0,match.start()-80):match.start()]
            # Negation, requests for mandates and hypothetical claims are not evidence.
            if re.search(r'\b(non|senza|nessun[oa]?|cerchiamo|cercasi|richied|ricerc|possibil|eventual|ipotetic)',before,re.I):continue
            if re.match(r'[^.!?\n]{0,35}\b(non|inesistente|scadut[oa]|revocat[oa])\b',text[match.end():],re.I):continue
            quote=text[max(text.rfind('\n',0,match.start())+1,match.start()-35):min(len(text),match.end()+65)].strip()
            found.append({'kind':kind,'label':label,'quote':quote,'source_url':p.get('url','')})
    if len({x['kind'] for x in found})>1:return {'kind':'unknown','label':'Ruolo da verificare','quote':'','source_url':p.get('url','')}
    return found[0] if found else {'kind':'unknown','label':'Filiera da verificare','quote':'','source_url':p.get('url','')}
