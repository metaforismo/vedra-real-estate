"""Controlled run and AI-response evidence for local UI tests; no model calls."""
from app.db import dump, now, uid
from app.schemas import Criteria
from app.services.store import agent_dict, property_dict, refresh_analysis, link_agent
from app.services.analysis import validate_semantic


def research_review(db):
    pid=db.one("SELECT id FROM properties WHERE title LIKE 'Spazi direzionali%' LIMIT 1")['id']
    p=property_dict(db.one('SELECT * FROM properties WHERE id=?',(pid,)))
    prompt='Cambio d’uso esplicito\nMandato esclusivo documentato'
    criteria=Criteria(custom_prompt=prompt,research_instructions='Visita prima il catalogo del broker. Controlla chi gestisce il bene.',max_price=2000000).model_dump()
    aid=uid();rid=uid()
    db.execute('INSERT INTO agents VALUES(?,?,?,?,?,?,0,1,NULL,?,?)',
        (aid,'Ricerca · collaudo criteri','Milano',dump(criteria),dump([p['source_id'],'demo-monza']),'hermes',now(),now()))
    agent=agent_dict(db.one('SELECT * FROM agents WHERE id=?',(aid,)))
    db.execute('''INSERT INTO runs(id,agent_id,status,trigger,runtime,created_at,collected,stats,config_snapshot)
        VALUES(?,?,'running','manual','hermes',?,1,?,?)''',
        (rid,aid,now(),dump({'processed':1,'new':0,'changed':0,'errors':1,'sources_ok':1,'sources_total':2}),dump(agent)))
    payload=p|{'custom_prompt':prompt}
    db.execute('INSERT INTO semantic_tasks VALUES(?,?,?,?,0)',(rid,pid,p['content_hash'],dump(payload)))
    db.event(rid,'research_brief','Brief di collaudo consegnato.',data={'targets':[{'name':'Catalogo di collaudo','url':'https://catalog.example/broker'}]})
    db.event(rid,'browser','Pagina acquisita nel collaudo.',data={'url':'https://catalog.example/broker'})
    # A submitted response may still contain an uncertain requirement. The UI must keep it visible.
    raw={'summary':'Risposta AI di collaudo.','custom_assessment':{'status':'uncertain','reason':'Il mandato non è documentato.',
        'evidence':['possibile cambio d’uso'],'checks':[
            {'criterion':prompt.splitlines()[0],'status':'matched','reason':'Possibilità dichiarata nel testo.','evidence':['possibile cambio d’uso']},
            {'criterion':prompt.splitlines()[1],'status':'uncertain','reason':'Mandato non documentato nella fonte.','evidence':[]}]}}
    refresh_analysis(db,pid,validate_semantic(payload,raw));link_agent(db,agent,pid)
    return aid,rid,pid
