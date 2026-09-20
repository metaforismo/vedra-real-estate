import pytest
from app.db import dump,load,now
from app.services.engine import Engine
from app.services.origination import Origination
from app.connectors.safe_http import SafeFetcher
from support.catalog import seed

@pytest.fixture
def online(db,settings):
    seed(db,settings)
    row=db.one("SELECT * FROM agents WHERE id='agent-milano'");c=load(row['criteria']);c['online_discovery']=True;c['max_listings']=1;c['min_surface']=0;c['property_types']=[]
    db.execute("UPDATE agents SET runtime='hermes',criteria=?,source_ids=? WHERE id='agent-milano'",(dump(c),dump(['web'])))
    db.execute('INSERT INTO sources(id,name,kind,domain,config,permission_at,created_at) VALUES(?,?,?,?,?,?,?)',('web','Web','html','catalog.example',dump({'search_url':'https://catalog.example/search','listing_url_pattern':'/listing/','retain_raw_html':False}),now(),now()))
    settings.live_domains=['catalog.example'];settings.request_delay=0
    engine=Engine(db,settings);rid=engine.enqueue('agent-milano')['id'];db.execute("UPDATE runs SET status='running' WHERE id=?",(rid,))
    return Origination(engine),rid

async def test_hermes_discovers_then_acquires_source_facts(online,monkeypatch):
    service,rid=online;seen=[]
    async def fetch(self,url):
        seen.append(url)
        if url.endswith('/search'):return '<a href="/listing/one">One</a><a href="/listing/two">Two</a>',url
        return '''<script type="application/ld+json">{"@type":"Apartment","name":"Test property","description":"Appartamento da ristrutturare","offers":{"price":550000,"priceCurrency":"EUR","businessFunction":"Sell"},"floorSize":{"value":90},"address":{"addressLocality":"Milano"}}</script>''',url
    monkeypatch.setattr(SafeFetcher,'get',fetch)
    with pytest.raises(ValueError,match='Nessun annuncio'):await service.complete(rid)
    with pytest.raises(ValueError,match='URL non presente'):await service.acquire(rid,'https://127.0.0.1/private')
    await service.search(rid);await service.search(rid)
    assert len(seen)==1
    result=await service.acquire(rid,'https://catalog.example/listing/one')
    assert result['listing']['price']==550000
    assert load(service.db.one('SELECT stats FROM runs WHERE id=?',(rid,))['stats'])['processed']==1
    assert (await service.acquire(rid,'https://catalog.example/listing/one'))['already_acquired']
    with pytest.raises(ValueError,match='Limite'):await service.acquire(rid,'https://catalog.example/listing/two')
    done=await service.complete(rid);assert done['pending']==1
    assert load(service.db.one('SELECT stats FROM runs WHERE id=?',(rid,))['stats'])['discovery']=='hermes'
    with pytest.raises(ValueError,match='chiusa'):await service.acquire(rid,'https://catalog.example/listing/two')

async def test_cancel_during_fetch_prevents_persisting(online,monkeypatch):
    service,rid=online
    async def fetch(self,url):
        service.db.execute("UPDATE runs SET status='cancelling' WHERE id=?",(rid,))
        return '<a href="/listing/one">One</a>',url
    monkeypatch.setattr(SafeFetcher,'get',fetch)
    from app.services.engine import RunCancelled
    with pytest.raises(RunCancelled):await service.search(rid)
    assert not service.db.all("SELECT * FROM events WHERE run_id=? AND step='hermes_discovery'",(rid,))

async def test_source_failure_remains_visible(online,monkeypatch):
    service,rid=online
    async def fetch(self,url):raise RuntimeError('unavailable')
    monkeypatch.setattr(SafeFetcher,'get',fetch)
    with pytest.raises(ValueError,match='non raggiungibile'):await service.search(rid)
    source=service.db.one("SELECT status FROM sources WHERE id='web'")
    assert source['status']=='blocked'
    assert service.db.one("SELECT COUNT(*) n FROM events WHERE run_id=? AND level='error'",(rid,))['n']==1
    assert not service.db.all('SELECT * FROM run_properties WHERE run_id=?',(rid,))

async def test_online_starts_hermes_without_backend_precollection(online,monkeypatch):
    service,rid=online
    calls=[]
    async def forbidden_collect(*args):raise AssertionError('Backend precollection is forbidden')
    async def start(self,run_id,capability,online=False):
        calls.append((run_id,online))
        service.db.execute('UPDATE runs SET collected=1,analysis_done=1 WHERE id=?',(run_id,))
        return 'remote-test'
    async def status(self,remote_id):return {'status':'completed'}
    from app.services.hermes import HermesClient
    monkeypatch.setattr(service.engine,'collect',forbidden_collect)
    monkeypatch.setattr(HermesClient,'start',start)
    monkeypatch.setattr(HermesClient,'status',status)
    await service.engine._execute(rid)
    assert calls==[(rid,True)]
    # A model claiming completion without real collection still cannot succeed.
    assert service.db.one('SELECT status FROM runs WHERE id=?',(rid,))['status']=='failed'
