from datetime import date
import re
from .catalog import by_ids
from .decision_facts import dossier
from .asset_evidence import AssetEvidence
from .decision_support import DecisionSupport


def contact_history(db,pid):
    return db.all('SELECT c.*,u.name author FROM contact_actions c JOIN users u ON u.id=c.user_id WHERE c.property_id=? ORDER BY c.created_at DESC,c.id DESC',(pid,))


def queue(db):
    today=date.today().isoformat()
    rows=db.all("""WITH ranked_contacts AS (
        SELECT property_id,outcome,next_contact,
               ROW_NUMBER() OVER(PARTITION BY property_id ORDER BY created_at DESC,id DESC) n
        FROM contact_actions)
        SELECT p.id FROM properties p LEFT JOIN ranked_contacts c ON c.property_id=p.id AND c.n=1
        WHERE p.is_demo=0 AND p.availability='listed'
        AND p.review_status NOT IN ('acquired','discarded')
        AND (p.review_status IN ('shortlisted','due_diligence','negotiation') OR EXISTS(
            SELECT 1 FROM agent_properties a WHERE a.property_id=p.id AND a.fit=1))
        AND (c.property_id IS NULL OR (c.outcome!='not_relevant'
             AND (c.outcome NOT IN ('reached','documents_requested') OR c.next_contact IS NOT NULL)
             AND (c.next_contact IS NULL OR c.next_contact<=?)))
        ORDER BY (c.next_contact IS NULL),c.next_contact,p.priority_score DESC,p.last_seen DESC,p.id LIMIT 101""",(today,))
    call=[];verify=[];assets=AssetEvidence(db);candidates={}
    ids=[r['id'] for r in rows[:100]];support=DecisionSupport(db,ids,assets)
    for p in by_ids(db,ids):
        latest=assets.latest_contact(p['id'])
        history=[latest] if latest else []
        if latest and (latest['outcome']=='not_relevant' or (latest['outcome'] in ('reached','documents_requested') and not latest['next_contact']) or (latest['next_contact'] and latest['next_contact']>today)):continue
        facts=dossier(p,calls=history[:1]);contact=facts.get('contact') or {}
        reasons=['Nei criteri di '+m['name'] for m in p.get('search_matches',[]) if m['fit']]
        if not reasons:reasons=['Selezionato dal team']
        if p.get('discount') is not None:reasons.append(f"Scarto dal benchmark: {-p['discount']:+.1f}%")
        item={k:p[k] for k in ('id','title','city','url','price','currency','priority_score','last_seen','source_name','signals','discount')}
        cross=assets.for_property(p)
        item.update(contact=contact,contact_route=facts['contact_route'],reasons=reasons,last_contact=latest,linked_count=cross['count'],checks=cross['conflicts'])
        age=support.freshness(p);item['freshness']=age
        if age['status']=='stale':item['checks']=[*item['checks'],'Disponibilità da ricontrollare']
        needs_check=age['status']=='stale' or cross['identity_conflict'] or cross['availability_conflict'] or cross['limited']
        phone=contact.get('telephone');email=contact.get('email')
        reachable=bool(isinstance(phone,str) and re.fullmatch(r'\+?\d{6,16}',phone) or
                       isinstance(email,str) and re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+',email))
        if not reachable:item['checks']=[*item['checks'],'Recapito da trovare']
        if cross['limited']:item['checks']=[*item['checks'],'Collegamenti da completare']
        callable=reachable and not needs_check
        root=assets.root(p['id']);previous=candidates.get(root)
        if previous is None or (callable,facts['contact_route']['kind']!='unknown')>(previous[1],previous[0]['contact_route']['kind']!='unknown'):
            candidates[root]=(item,callable)
    for item,callable in candidates.values():(call if callable else verify).append(item)
    sort=lambda x:(0 if x['last_contact'] and x['last_contact']['next_contact'] else 1,(x['last_contact']['next_contact'] or '') if x['last_contact'] else '',0 if x['contact_route']['kind']!='unknown' else 1,-(x['priority_score'] or 0),x['id'])
    return {'call':sorted(call,key=sort),'verify':sorted(verify,key=sort),'limited':len(rows)>100,'examined':len(ids)}
