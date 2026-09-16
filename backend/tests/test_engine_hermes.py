import json
import httpx
import pytest
from app.db import dump,load,now
from app.services.seed import seed
from app.services.engine import Engine
from app.services.hermes import HermesClient,HermesUnavailable
from app.services.store import property_dict,upsert_listing

async def test_local_full_run_is_real_and_idempotent(db,settings):
    seed(db,settings);engine=Engine(db,settings)
    run=engine.enqueue('agent-milano')
    await engine.execute(run['id'])
    result=db.one('SELECT * FROM runs WHERE id=?',(run['id'],))
    assert result['status']=='completed' and result['analysis_done']
    stats=load(result['stats']);assert stats['found']==12 and stats['processed']==12 and stats['new']==0 and stats['errors']==0
    assert all('hermes' not in load(p['analysis'])['engine'] for p in db.all('SELECT analysis FROM properties'))
    assert db.one('SELECT COUNT(*) n FROM observations')['n']==36

async def test_bad_source_is_failure_not_empty_market(db,settings,monkeypatch):
    seed(db,settings);engine=Engine(db,settings)
    db.execute("UPDATE sources SET kind='html',domain='catalog.example',permission_at=?,config=? WHERE id='demo-milano'",(now(),dump({'search_url':'https://catalog.example/search'})))
    from app.connectors.safe_http import SafeFetcher,SourceBlocked
    async def block(*_):raise SourceBlocked('HTTP 403 mock')
    monkeypatch.setattr(SafeFetcher,'get',block)
    run=engine.enqueue('agent-milano');await engine.execute(run['id'])
    result=db.one('SELECT * FROM runs WHERE id=?',(run['id'],));assert result['status']=='failed'
    assert load(result['stats'])['errors']==1
    assert db.one("SELECT status FROM sources WHERE id='demo-milano'")['status']=='blocked'

async def test_hermes_http_contract(settings):
    calls=[]
    def handle(req):
        assert req.headers['authorization']=='Bearer test-only-hermes-key'
        calls.append(req)
        if req.url.path=='/v1/capabilities':return httpx.Response(200,json={'features':{'run_submission':True,'run_status':True,'run_stop':True}})
        if req.url.path=='/v1/toolsets':return httpx.Response(200,json=[{'enabled':True,'tools':['mcp_vedra_get_tasks','mcp_vedra_submit_analysis','mcp_vedra_finish_run']}])
        if req.method=='POST' and req.url.path=='/v1/runs':
            body=json.loads(req.content);assert body['session_id']=='vedra-abc-123' and 'mcp_vedra_get_tasks' in body['input']
            assert req.headers['idempotency-key']=='vedra-abc-123'
            return httpx.Response(202,json={'run_id':'run_test','status':'started'})
        if req.url.path.endswith('/stop'):return httpx.Response(200,json={'status':'stopping'})
        return httpx.Response(200,json={'status':'completed','usage':{'input_tokens':10}})
    client=HermesClient(settings,transport=httpx.MockTransport(handle))
    rid=await client.start('abc-123','0'*64);assert rid=='run_test'
    assert (await client.status(rid))['status']=='completed'
    assert (await client.stop(rid))['status']=='stopping'
    assert len(calls)==5

async def test_hermes_capabilities_fail_closed(settings):
    client=HermesClient(settings,transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'features':{}})))
    with pytest.raises(HermesUnavailable):await client.start('test')

async def test_upstream_secret_not_exposed(settings):
    client=HermesClient(settings,transport=httpx.MockTransport(lambda r:httpx.Response(401,text='password=secret-12345')))
    with pytest.raises(HermesUnavailable) as error:await client.capabilities()
    assert 'secret-12345' not in str(error.value)

async def test_no_silent_ai_fallback(db,settings,monkeypatch):
    seed(db,settings);db.execute("UPDATE agents SET runtime='hermes' WHERE id='agent-milano'")
    async def fail(*_):raise HermesUnavailable('mock unavailable')
    monkeypatch.setattr(HermesClient,'start',fail)
    engine=Engine(db,settings);run=engine.enqueue('agent-milano');await engine.execute(run['id'])
    result=db.one('SELECT * FROM runs WHERE id=?',(run['id'],))
    assert result['status']=='failed' and result['collected']==1 and result['analysis_done']==0

async def test_bridge_reclassifies_old_rules_and_requires_every_task(api):
    app,c,s=api;db=app.state.db;engine=app.state.engine
    # Old records from the seed have not changed, but still need semantic analysis.
    db.execute("UPDATE agents SET runtime='hermes' WHERE id='agent-monza'")
    run=engine.enqueue('agent-monza');rid=run['id']
    db.execute("UPDATE runs SET status='running' WHERE id=?",(rid,))
    headers={'Authorization':'Bearer '+s.bridge_token}
    assert c.post(f'/bridge/runs/{rid}/collect',headers={'Authorization':'Bearer bad'}).status_code==401
    collect=c.post(f'/bridge/runs/{rid}/collect',headers=headers)
    assert collect.status_code==200,collect.text
    tasks=collect.json()['properties'];assert len(tasks)>0
    assert collect.json()['stats']['new']==0
    assert c.post(f'/bridge/runs/{rid}/finish',headers=headers).status_code==409
    # Collection is idempotent, not another browsing pass.
    assert c.post(f'/bridge/runs/{rid}/collect',headers=headers).json()==collect.json()
    assert c.post(f'/bridge/runs/{rid}/analysis/wrong-id',headers=headers,json={'summary':'Test'}).status_code==403
    task=tasks[0]
    invented={'summary':'Non validato','strategies':[{'strategy':'value_add','evidence':'rendimento garantito del 20%'}]}
    assert c.post(f"/bridge/runs/{rid}/analysis/{task['id']}",headers=headers,json=invented).status_code==422
    seen=set()
    assert len(tasks)<=10
    while tasks:
        for task in tasks:
            assert task['id'] not in seen
            seen.add(task['id'])
            payload={'summary':'Sintesi dimostrativa del testo fornito.','strategies':[],'caveats':['Test di contratto, non chiamata LLM reale.']}
            response=c.post(f"/bridge/runs/{rid}/analysis/{task['id']}",headers=headers,json=payload)
            assert response.status_code==200,response.text
        status=c.get(f'/bridge/runs/{rid}',headers=headers).json()
        tasks=status['properties']
        assert len(tasks)<=10
    assert len(seen)==collect.json()['task_total'] and status['pending']==0
    assert c.post(f'/bridge/runs/{rid}/finish',headers=headers).status_code==200
    assert db.one('SELECT analysis_done FROM runs WHERE id=?',(rid,))['analysis_done']==1
    engine.finish(rid)
    db.execute("UPDATE agents SET runtime='local' WHERE id='agent-monza'")

async def test_immutable_evidence_conflict(api):
    app,c,s=api;db=app.state.db;engine=app.state.engine
    db.execute("UPDATE agents SET runtime='hermes' WHERE id='agent-como'")
    run=engine.enqueue('agent-como');rid=run['id'];db.execute("UPDATE runs SET status='running' WHERE id=?",(rid,))
    headers={'Authorization':'Bearer '+s.bridge_token}
    task=c.post(f'/bridge/runs/{rid}/collect',headers=headers).json()['properties'][0]
    original=db.one('SELECT content_hash FROM properties WHERE id=?',(task['id'],))['content_hash']
    db.execute('UPDATE properties SET content_hash=? WHERE id=?',('changed-content',task['id']))
    try:assert c.post(f"/bridge/runs/{rid}/analysis/{task['id']}",headers=headers,json={'summary':'Test'}).status_code==409
    finally:
        db.execute('UPDATE properties SET content_hash=? WHERE id=?',(original,task['id']))
        engine.finish(rid,'cancelled');db.execute("UPDATE agents SET runtime='local' WHERE id='agent-como'")

async def test_external_scheduler_cannot_duplicate_clock(api):
    app,c,s=api
    assert c.post('/bridge/agents/agent-milano/enqueue',headers={'Authorization':'Bearer '+s.bridge_token}).status_code==409


async def test_hermes_empty_delta_costs_no_model_call(db,settings,monkeypatch):
    seed(db,settings)
    db.execute("UPDATE agents SET runtime='hermes' WHERE id='agent-milano'")
    for p in db.all("SELECT id,analysis FROM properties WHERE city='Milano'"):
        analysis=load(p['analysis']);analysis['engine']='hermes'
        db.execute('UPDATE properties SET analysis=? WHERE id=?',(dump(analysis),p['id']))
    async def forbidden(*_):raise AssertionError('No LLM call expected for an empty semantic delta')
    monkeypatch.setattr(HermesClient,'start',forbidden)
    engine=Engine(db,settings);run=engine.enqueue('agent-milano')
    await engine.execute(run['id'])
    assert db.one('SELECT status FROM runs WHERE id=?',(run['id'],))['status']=='completed'
    assert not db.all('SELECT * FROM semantic_tasks WHERE run_id=?',(run['id'],))
    assert any('nessun modello' in x['message'] for x in db.all('SELECT message FROM events WHERE run_id=?',(run['id'],)))
