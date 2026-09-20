from __future__ import annotations

import hashlib
from pathlib import Path

from ..db import Database, dump, load, now, uid
from ..schemas import Listing
from ..connectors.parser import PARSER_VERSION
from .property_index import index_strategies, observation_payload
from .analysis import classify_rules, completeness, match_benchmark, opportunity, screen

JSON_FIELDS=('images','evidence','analysis','benchmark','score_breakdown')


def property_dict(row: dict) -> dict:
    row=dict(row)
    for key in JSON_FIELDS:
        row[key]=load(row.get(key), [] if key in ('images','score_breakdown') else None if key=='benchmark' else {})
    row['price_sqm']=round(row['price']/row['surface'],2) if row.get('price') and row.get('surface') else None
    row['is_demo']=bool(row['is_demo'])
    row['starred']=bool(row['starred'])
    row['missing_fields']=completeness(row)[1]
    return row


def agent_dict(row: dict) -> dict:
    row=dict(row)
    row['criteria']=load(row['criteria'],{})
    row['source_ids']=load(row['source_ids'],[])
    row['active']=bool(row['active'])
    return row


def list_properties(db: Database, *, dataset='real',city='',q='',starred=False,status='',agent_id='') -> list[dict]:
    where=[]; args=[]
    from ..datasets import require_real_dataset
    require_real_dataset(dataset)
    if dataset == 'real':
        where.append('p.is_demo=?');args.append(1 if dataset=='demo' else 0)
    if city: where.append('lower(p.city)=lower(?)');args.append(city)
    if q:
        where.append('(p.title LIKE ? OR p.address LIKE ? OR p.city LIKE ?)')
        args.extend([f'%{q}%']*3)
    if starred: where.append('p.starred=1')
    if status: where.append('p.review_status=?');args.append(status)
    if agent_id:
        where.append('EXISTS(SELECT 1 FROM agent_properties ap WHERE ap.property_id=p.id AND ap.agent_id=?)');args.append(agent_id)
    sql='SELECT p.*,s.name as source_name FROM properties p JOIN sources s ON s.id=p.source_id'
    if where: sql+=' WHERE '+' AND '.join(where)
    sql+=' ORDER BY (p.score IS NULL),p.score DESC,p.last_seen DESC LIMIT 2000'
    return [property_dict(r) for r in db.all(sql,tuple(args))]


def upsert_listing(db: Database, settings, source_id: str, listing: Listing, *, raw: str='',run_id: str | None=None) -> tuple[str,bool,bool]:
    p=listing.model_dump()
    # Runtime evidence is assigned by the importer/connector, not trusted CSV input.
    content={k:v for k,v in p.items() if k not in ('evidence','is_demo')}
    digest=hashlib.sha256(dump(content).encode()).hexdigest()
    old=db.one('SELECT * FROM properties WHERE source_id=? AND listing_key=?',(source_id,p['listing_key']))
    created=old is None
    changed=created or old['content_hash']!=digest
    pid=old['id'] if old else uid()
    analysis=classify_rules(p)
    if old and not changed:
        analysis=load(old['analysis'],analysis)
    benchmarks=db.all('SELECT * FROM benchmarks')
    benchmark,unavailable=match_benchmark(p,benchmarks)
    if not benchmark:
        analysis['benchmark_note']=unavailable
    score,discount,breakdown=opportunity(p,benchmark,analysis)
    quality,_=completeness(p)
    timestamp=now()
    snapshot=None
    if changed and raw:
        snapshot=f'snapshots/{pid}/{digest}.txt'
        target=settings.data_dir/snapshot
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(raw[:settings.max_html_bytes])
    values={**p,'id':pid,'first_seen':old['first_seen'] if old else timestamp,'last_seen':timestamp,
            'content_hash':digest,'completeness':quality,'analysis':analysis,'benchmark':benchmark,
            'score':score,'score_breakdown':breakdown,'discount':discount,'source_id':source_id}
    for key in JSON_FIELDS:
        values[key]=dump(values[key]) if values[key] is not None else None
    keys=list(values)
    with db.transaction() as con:
        if created:
            con.execute(f"INSERT INTO properties({','.join(keys)}) VALUES({','.join('?' for _ in keys)})",tuple(values[k] for k in keys))
        else:
            update=[k for k in keys if k not in ('id','first_seen','source_id','listing_key')]
            con.execute(f"UPDATE properties SET {','.join(k+'=?' for k in update)} WHERE id=?",tuple(values[k] for k in update)+(pid,))
        index_strategies(con, pid, analysis)
        con.execute('INSERT INTO listing_checks VALUES(?,?) ON CONFLICT(property_id) DO UPDATE SET last_detail_at=excluded.last_detail_at', (pid,timestamp))
        if changed:
            oid=uid()
            con.execute('INSERT INTO observations VALUES(?,?,?,?,?,?,?)',(oid,pid,timestamp,p['price'],digest,snapshot,PARSER_VERSION))
            con.execute('INSERT INTO observation_values VALUES(?,?)', (oid,observation_payload(p)))
            con.execute('INSERT INTO observation_context VALUES(?,?,?,?,?)',
                        (oid,p['currency'],p['transaction_type'],p['area_basis'],p['surface']))
        if run_id:
            con.execute('INSERT INTO run_properties VALUES(?,?,?) ON CONFLICT DO NOTHING',(run_id,pid,int(changed)))
    if run_id and changed:
        from .operations import notify
        if created or (old and old['price'] != p['price']):
            kind='new_property' if created else 'price_change'
            notify(db,settings,kind=kind,title='Nuovo immobile' if created else 'Prezzo modificato',
                   body=p['title'],property_id=pid,run_id=run_id,is_demo=p['is_demo'],
                   dedupe_key=f'{kind}:{pid}:{digest}:{run_id}')
    return pid,created,changed


def refresh_analysis(db: Database,pid: str,analysis: dict | None=None) -> dict:
    row=db.one('SELECT * FROM properties WHERE id=?',(pid,))
    if not row: raise ValueError('Immobile non trovato')
    p=property_dict(row)
    analysis=analysis or p['analysis'] or classify_rules(p)
    benchmark,note=match_benchmark(p,db.all('SELECT * FROM benchmarks'))
    analysis=dict(analysis)
    analysis.pop('benchmark_note',None)
    if not benchmark: analysis['benchmark_note']=note
    score,discount,breakdown=opportunity(p,benchmark,analysis)
    with db.transaction() as con:
        con.execute('UPDATE properties SET analysis=?,benchmark=?,score=?,discount=?,score_breakdown=? WHERE id=?',
                    (dump(analysis),dump(benchmark) if benchmark else None,score,discount,dump(breakdown),pid))
        index_strategies(con, pid, analysis)
    for row in db.all('SELECT a.* FROM agents a JOIN agent_properties ap ON a.id=ap.agent_id WHERE ap.property_id=?',(pid,)):
        link_agent(db,agent_dict(row),pid)
    return property_dict(db.one('SELECT * FROM properties WHERE id=?',(pid,)))


def link_agent(db: Database,agent: dict,pid: str):
    p=property_dict(db.one('SELECT * FROM properties WHERE id=?',(pid,)))
    fit,reasons=screen(p,agent)
    db.execute('''INSERT INTO agent_properties VALUES(?,?,?,?,?) ON CONFLICT(agent_id,property_id)
                   DO UPDATE SET fit=excluded.fit,fit_reasons=excluded.fit_reasons,score=excluded.score''',
               (agent['id'],pid,int(fit),dump(reasons),p['score']))
