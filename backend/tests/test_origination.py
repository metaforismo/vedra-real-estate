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


async def test_hermes_honors_source_rendering_for_search_and_detail(online,monkeypatch):
    service,rid=online;seen=[]
    config=load(service.db.one("SELECT config FROM sources WHERE id='web'")['config'])
    config['render_js']=True
    service.db.execute("UPDATE sources SET config=? WHERE id='web'",(dump(config),))
    async def plain(*args):raise AssertionError('Rendering preference was ignored')
    async def rendered(self,url):
        seen.append(url)
        if url.endswith('/search'):return '<a href="/listing/one">One</a>',url
        return '<script type="application/ld+json">{"@type":"Apartment","name":"Appartamento venduto","offers":{"price":550000,"priceCurrency":"EUR"}}</script>',url
    monkeypatch.setattr(SafeFetcher,'get',plain)
    monkeypatch.setattr(SafeFetcher,'rendered',rendered)
    await service.search(rid)
    await service.acquire(rid,'https://catalog.example/listing/one')
    assert seen==['https://catalog.example/search','https://catalog.example/listing/one']


async def test_discovery_context_is_bounded_deduplicated_and_repeatable(online,monkeypatch):
    service,rid=online
    service.db.execute("UPDATE sources SET config=? WHERE id='web'",(dump({'search_url':'https://catalog.example/search','listing_url_pattern':'/listing/','next_selector':'.next','max_pages':2}),))
    async def fetch(self,url):
        return '<div class="wdk-listing-card"><a href="/listing/one">Bilocale Argonne</a><span class="wdk-price">  550.000   €  </span></div><a class="next" href="/search?page=2">Next</a>',url
    monkeypatch.setattr(SafeFetcher,'get',fetch)
    result=await service.search(rid)
    candidate=result['sources'][0]['candidates']
    assert len(candidate)==1 and 'Argonne' in candidate[0]['source_text_hint']
    assert candidate[0]['asking_price_hint']=='550.000 €'
    assert (await service.search(rid))['sources']==result['sources']

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

async def test_known_missing_from_catalog_is_mandatory_refresh(online,monkeypatch):
    from app.schemas import Listing
    from app.services.store import upsert_listing,link_agent,agent_dict
    service,rid=online;db=service.db
    p=Listing(listing_key='old',url='https://catalog.example/listing/old',title='Old',city='Milano',price=550000,surface=80,currency='EUR',transaction_type='sale')
    pid,_,_=upsert_listing(db,service.settings,'web',p)
    agent=agent_dict(db.one("SELECT * FROM agents WHERE id='agent-milano'"));link_agent(db,agent,pid)
    db.execute("UPDATE listing_checks SET last_detail_at='2020-01-01T00:00:00+00:00' WHERE property_id=?",(pid,))
    async def fetch(self,url):
        if url.endswith('/search'):return '<a href="/listing/new">New</a>',url
        return '<h1>Immobile</h1><script type="application/ld+json">{"@type":"Apartment","name":"Old","offers":{"price":550000,"priceCurrency":"EUR"}}</script>',url
    monkeypatch.setattr(SafeFetcher,'get',fetch)
    found=await service.search(rid)
    assert found['sources'][0]['refresh_urls']==[p.url]
    assert p.url in found['sources'][0]['urls']
    await service.acquire(rid,'https://catalog.example/listing/new')
    with pytest.raises(ValueError,match='Ricontrolla'):await service.complete(rid)
    await service.acquire(rid,p.url)
    await service.complete(rid)
    assert len(db.all('SELECT * FROM run_properties WHERE run_id=?',(rid,)))==2

async def test_missing_detail_is_not_a_sale_or_a_source_outage(online,monkeypatch):
    from app.schemas import Listing
    from app.services.store import upsert_listing,link_agent,agent_dict
    from app.connectors.safe_http import SourceBlocked
    service,rid=online;db=service.db
    p=Listing(listing_key='old',url='https://catalog.example/listing/old',title='Old',price=550000,surface=80)
    pid,_,_=upsert_listing(db,service.settings,'web',p)
    link_agent(db,agent_dict(db.one("SELECT * FROM agents WHERE id='agent-milano'")),pid)
    async def fetch(self,url):
        if url.endswith('/search'):return '<a href="/listing/old">Old</a>',url
        raise SourceBlocked('La fonte risponde HTTP 404.')
    monkeypatch.setattr(SafeFetcher,'get',fetch)
    await service.search(rid)
    result=await service.acquire(rid,p.url)
    assert result['availability']=='review'
    assert db.one('SELECT availability FROM properties WHERE id=?',(pid,))['availability']=='review'
    assert not db.one("SELECT * FROM source_health WHERE source_id='web'")
    assert db.one('SELECT fit FROM agent_properties WHERE property_id=?',(pid,))['fit']==0

async def test_successful_catalog_without_new_listings_can_complete(online,monkeypatch):
    service,rid=online
    async def fetch(self,url):return '<a href="/listing/one">Outside criteria</a>',url
    monkeypatch.setattr(SafeFetcher,'get',fetch)
    await service.search(rid)
    await service.complete(rid)
    run=service.db.one('SELECT * FROM runs WHERE id=?',(rid,))
    assert run['collected']==1 and load(run['stats'])['processed']==0

async def test_hermes_receives_sale_evidence_and_next_action(online,monkeypatch):
    service,rid=online
    async def fetch(self,url):
        if url.endswith('/search'):return '<a href="/listing/one">One</a>',url
        return '<h1>Appartamento venduto</h1><script type="application/ld+json">{"@type":"Apartment","name":"Appartamento venduto","offers":{"price":550000,"priceCurrency":"EUR"}}</script>',url
    monkeypatch.setattr(SafeFetcher,'get',fetch)
    await service.search(rid)
    result=await service.acquire(rid,'https://catalog.example/listing/one')
    assert result['availability_check']['status']=='sold'
    assert result['availability_check']['excluded'] is True
    assert 'continue searching' in result['next_action']
    event=service.db.one("SELECT data FROM events WHERE run_id=? AND step='availability'",(rid,))
    assert load(event['data'])['evidence']['value']=='venduto'
    await service.complete(rid)
    assert not service.db.all('SELECT * FROM semantic_tasks WHERE run_id=?',(rid,))

async def test_blocked_portal_does_not_stop_other_sources(online,monkeypatch):
    service,rid=online;db=service.db
    db.execute('INSERT INTO sources(id,name,kind,domain,config,permission_at,created_at) VALUES(?,?,?,?,?,?,?)',
               ('second','Other portal','html','second.example',dump({'search_url':'https://second.example/search','listing_url_pattern':'/listing/'}),now(),now()))
    snapshot=load(db.one('SELECT config_snapshot FROM runs WHERE id=?',(rid,))['config_snapshot'])
    snapshot['source_ids']=['web','second']
    db.execute('UPDATE runs SET config_snapshot=? WHERE id=?',(dump(snapshot),rid))
    service.settings.live_domains.append('second.example')
    async def fetch(self,url):
        from app.connectors.safe_http import SourceBlocked
        if self.domain=='catalog.example':raise SourceBlocked('HTTP 403')
        return '<a href="/listing/one">Other source</a>',url
    monkeypatch.setattr(SafeFetcher,'get',fetch)
    result=await service.search(rid)
    assert len(result['sources'])==2
    assert result['sources'][0]['error'] and result['sources'][1]['urls']==['https://second.example/listing/one']
    repeat=await service.search(rid)
    assert {x['source_id'] for x in repeat['sources']}=={'web','second'}
    await service.complete(rid)
    stats=load(db.one('SELECT stats FROM runs WHERE id=?',(rid,))['stats'])
    assert stats['sources_ok']==1 and stats['errors']==1

@pytest.fixture
def browser_online(online):
    service,rid=online
    cfg=load(service.db.one("SELECT config FROM sources WHERE id='web'")['config'])
    cfg.update(browser_navigation=True,next_selector='a[rel=next]',max_pages=2)
    service.db.execute("UPDATE sources SET config=? WHERE id='web'",(dump(cfg),))
    return service,rid

async def test_browser_navigation_is_agent_driven_bounded_and_persisted(browser_online,monkeypatch):
    service,rid=browser_online;seen=[]
    async def plain(*args):raise AssertionError('Browser source must render')
    async def rendered(self,url):
        seen.append(url)
        if url.endswith('page=2'):return '<a href="/listing/two">Second</a><a rel="next" href="/search?page=3">Next</a>',url
        return '<a href="/listing/one">First</a><a rel="next" href="/search?page=2">Next</a>',url
    monkeypatch.setattr(SafeFetcher,'get',plain);monkeypatch.setattr(SafeFetcher,'browse',rendered)
    result=await service.search(rid)
    assert result['sources'][0]['requires_browser'] and not seen
    with pytest.raises(ValueError,match='Apri prima'):await service.complete(rid)
    with pytest.raises(ValueError,match='Collegamento'):await service.browse(rid,'web','f'*24)
    first=await service.browse(rid,'web','')
    assert first['next_ref'] and first['page_text']=='First Next'
    assert await service.browse(rid,'web','')==first and len(seen)==1
    # State is durable across service instances; opening is idempotent.
    restarted=Origination(service.engine)
    second=await restarted.browse(rid,'web',first['next_ref'])
    assert second['next_ref']=='' and len(second['candidates'])==2
    assert len(service.db.all("SELECT * FROM events WHERE run_id=? AND step='hermes_discovery'",(rid,)))==1
    with pytest.raises(ValueError,match='Collegamento'):await restarted.browse(rid,'web',first['next_ref'])
    await restarted.complete(rid)
    stats=load(service.db.one('SELECT stats FROM runs WHERE id=?',(rid,))['stats'])
    assert stats['found']==2 and stats['sources_ok']==1

async def test_browser_challenge_cannot_complete_as_empty_catalog(browser_online,monkeypatch):
    from app.connectors.safe_http import SourceBlocked
    service,rid=browser_online
    async def blocked(*args):raise SourceBlocked('Access is temporarily restricted')
    monkeypatch.setattr(SafeFetcher,'browse',blocked)
    result=await service.browse(rid,'web','')
    assert result['error'] and not result['urls']
    with pytest.raises(ValueError,match='Nessun annuncio'):await service.complete(rid)
    assert service.db.one("SELECT status FROM sources WHERE id='web'")['status']=='blocked'

async def test_browser_cross_domain_pagination_is_not_exposed(browser_online,monkeypatch):
    service,rid=browser_online
    async def rendered(self,url):return '<a rel="next" href="https://private.example/admin">Next</a>',url
    monkeypatch.setattr(SafeFetcher,'browse',rendered)
    page=await service.browse(rid,'web','')
    assert not page['next_ref'] and not page['next_url']

async def test_browser_listing_is_saved_from_rendered_facts(browser_online,monkeypatch):
    service,rid=browser_online
    async def rendered(self,url):
        if url.endswith('/search'):return '<a href="/listing/one">First</a>',url
        return '<script type="application/ld+json">{"@type":"Apartment","name":"Sold flat","offers":{"price":550000,"priceCurrency":"EUR"}}</script><h1>Venduto</h1>',url
    monkeypatch.setattr(SafeFetcher,'browse',rendered)
    await service.browse(rid,'web','')
    acquired=await service.acquire(rid,'https://catalog.example/listing/one')
    assert acquired['listing']['price']==550000
    assert acquired['availability_check']['excluded']
    await service.complete(rid)

async def test_native_chromium_catalog_to_persisted_listing(browser_online,monkeypatch):
    """Real browser/TCP against a disposable fixture server, never a portal proof."""
    import os,threading
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    from urllib.parse import urlsplit,urlunsplit
    executable=os.getenv('BROWSER_TEST_EXECUTABLE')
    if not executable:pytest.skip('Set BROWSER_TEST_EXECUTABLE for the real Chromium integration check')
    service,rid=browser_online
    requests=[]
    class Fixture(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            if self.path.startswith('/redirect-'):
                target={'/redirect-safe':'/listing/one','/redirect-private':f'http://127.0.0.1:{self.server.server_port}/leak','/redirect-forbidden':'/private'}[self.path]
                self.send_response(302);self.send_header('Location',target);self.end_headers();return
            if self.path=='/robots.txt':body='User-agent: *\nDisallow: /private'
            elif self.path.startswith('/search'):
                # An HTML-only fetch cannot discover this injected link.
                body='''<html><body><h1>Fixture catalog</h1><script>
                const link=document.createElement('a');link.href='/listing/one';link.textContent='Fixture flat';document.body.append(link);
                if (typeof RTCPeerConnection !== 'undefined' || typeof WebTransport !== 'undefined' || typeof Worker !== 'undefined') document.body.append('UNSAFE');
                </script>''' + ''.join(f'<script src="/asset-{i}.js"></script>' for i in range(30)) + '</body></html>'
            elif self.path.startswith('/asset-'):
                self.send_response(200);self.send_header('Content-Type','application/javascript');self.end_headers()
                self.wfile.write(b'/* static dependency */');return
            else:body='''<script type="application/ld+json">{"@type":"Apartment","name":"Fixture flat","offers":{"price":550000,"priceCurrency":"EUR"},"floorSize":{"value":80},"address":{"addressLocality":"Milano"}}</script>'''
            self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(body.encode())
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Fixture)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    port=server.server_port
    config=load(service.db.one("SELECT config FROM sources WHERE id='web'")['config'])
    config['search_url']=f'http://catalog.example:{port}/search'
    service.db.execute("UPDATE sources SET config=? WHERE id='web'",(dump(config),))
    service.settings.browser_enabled=True;service.settings.browser_executable=executable
    original_validate=SafeFetcher.validate_url
    def fixture_url(self,url):
        p=urlsplit(url)
        assert p.port==port and p.hostname=='catalog.example'
        original_validate(self,urlunsplit((p.scheme,p.hostname,p.path,p.query,p.fragment)))
        return p
    async def fixture_resolve(self,host,port):
        assert host=='catalog.example'
        return '127.0.0.1'
    monkeypatch.setattr(SafeFetcher,'validate_url',fixture_url)
    monkeypatch.setattr(SafeFetcher,'resolve',fixture_resolve)
    try:
        # With the production delay applied to each static dependency this page
        # never reaches DOM ready within the navigation deadline.
        service.settings.request_delay=2
        page=await service.browse(rid,'web','')
        assert 'error' not in page,page
        assert len([p for p in requests if p.startswith('/asset-')])==30
        service.settings.request_delay=0
        assert page['candidates'][0]['source_text_hint']=='Fixture flat'
        assert 'UNSAFE' not in page['page_text']
        acquired=await service.acquire(rid,page['candidates'][0]['url'])
        assert acquired['listing']['price']==550000 and acquired['listing']['surface']==80
        assert service.db.one('SELECT price FROM properties WHERE id=?',(acquired['property_id'],))['price']==550000
        await service.complete(rid)
        from app.connectors.safe_http import SourceBlocked
        fetcher=SafeFetcher('catalog.example',service.settings)
        html,_=await fetcher.browse(f'http://catalog.example:{port}/redirect-safe')
        assert 'Fixture flat' in html
        for target in ('private','forbidden'):
            with pytest.raises(SourceBlocked):
                await fetcher.browse(f'http://catalog.example:{port}/redirect-{target}')
        assert '/leak' not in requests and '/private' not in requests
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)

async def test_browser_endpoint_uses_scoped_capability(browser_online,monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.security import token_hash
    from datetime import datetime,timedelta,timezone
    service,rid=browser_online
    token='a'*64
    service.db.execute('INSERT INTO run_capabilities VALUES(?,?,?)',(rid,token_hash(token),(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()))
    async def browse(self,url):return '<a href="/listing/one">One</a>',url
    monkeypatch.setattr(SafeFetcher,'browse',browse)
    app=create_app(service.settings)
    with TestClient(app) as client:
        endpoint=f'/bridge/runs/{rid}/browse'
        assert client.post(endpoint,json={'source_id':'web','ref':''}).status_code==401
        headers={'Authorization':'Bearer run:'+token}
        result=client.post(endpoint,headers=headers,json={'source_id':'web','ref':''})
        assert result.status_code==200,result.text
        assert result.json()['mode']=='browser'
        assert client.post(endpoint,headers=headers,json={'source_id':'web','ref':'','url':'https://example.com'}).status_code==422
        assert client.post(endpoint,headers=headers,json={'source_id':'other','ref':''}).status_code==422
        service.db.execute("UPDATE runs SET status='completed' WHERE id=?",(rid,))
        assert client.post(endpoint,headers=headers,json={'source_id':'web','ref':''}).status_code==401

async def test_browser_pagination_preserves_separate_refresh_allowance(browser_online,monkeypatch):
    from app.schemas import Listing
    from app.services.store import upsert_listing,link_agent,agent_dict
    service,rid=browser_online;db=service.db
    old=Listing(listing_key='old',url='https://catalog.example/listing/old',title='Old',city='Milano',price=550000,surface=80,currency='EUR',transaction_type='sale')
    pid,_,_=upsert_listing(db,service.settings,'web',old)
    link_agent(db,agent_dict(db.one("SELECT * FROM agents WHERE id='agent-milano'")),pid)
    async def browse(self,url):
        if url.endswith('/search'):return '<a rel="next" href="/search?page=2">Next</a>',url
        if url.endswith('page=2'):return '<a href="/listing/new">New</a>',url
        return '<script type="application/ld+json">{"@type":"Apartment","name":"Current flat","offers":{"price":550000,"priceCurrency":"EUR"}}</script>',url
    monkeypatch.setattr(SafeFetcher,'browse',browse)
    first=await service.browse(rid,'web','')
    assert old.url in first['refresh_urls']
    await service.acquire(rid,old.url)
    second=await service.browse(rid,'web',first['next_ref'])
    assert second['refresh_urls']==first['refresh_urls']
    result=await service.acquire(rid,'https://catalog.example/listing/new')
    assert result['new']
    await service.complete(rid)

@pytest.mark.parametrize('missing', [None, 'city', 'price', 'surface'])
def test_recent_incomplete_listing_requires_autonomous_refresh(online, missing):
    from app.schemas import Listing
    from app.services.store import upsert_listing, link_agent, agent_dict
    service, _ = online
    values = dict(listing_key='recent', url='https://catalog.example/listing/recent',
                  title='Recent', city='Milano', price=550000, surface=80,
                  availability='listed', currency='EUR', transaction_type='sale')
    if missing: values[missing] = '' if missing == 'city' else None
    listing = Listing(**values)
    pid, _, _ = upsert_listing(service.db, service.settings, 'web', listing)
    agent = agent_dict(service.db.one("SELECT * FROM agents WHERE id='agent-milano'"))
    link_agent(service.db, agent, pid)
    source = service.db.one("SELECT * FROM sources WHERE id='web'")
    refresh, _, _ = service.refresh_context(agent, source, {'detail_refresh_hours':6})
    assert refresh == ([listing.url] if missing else [])
    service.db.execute("UPDATE properties SET availability='sold' WHERE id=?", (pid,))
    assert service.refresh_context(agent, source, {'detail_refresh_hours':6})[0] == []

async def test_recent_and_closed_records_do_not_starve_new_browser_candidates(browser_online,monkeypatch):
    from app.schemas import Listing
    from app.services.store import upsert_listing,link_agent,agent_dict
    service,rid=browser_online;db=service.db;seen=[]
    agent=agent_dict(db.one("SELECT * FROM agents WHERE id='agent-milano'"))
    for key,status in [('recent','listed'),('closed','sold')]:
        p=Listing(listing_key=key,url=f'https://catalog.example/listing/{key}',title=key,
                  city='Milano',price=550000,surface=80,currency='EUR',transaction_type='sale')
        pid,_,_=upsert_listing(db,service.settings,'web',p);link_agent(db,agent,pid)
        db.execute('UPDATE properties SET availability=? WHERE id=?',(status,pid))
    async def browse(self,url):
        seen.append(url)
        if url.endswith('/search'):
            return ''.join(f'<a href="/listing/{key}">{key}</a>' for key in ['recent','closed','new']),url
        assert url.endswith('/new'),'Known records must not be downloaded again'
        return '<script type="application/ld+json">{"@type":"Apartment","name":"New","offers":{"price":550000,"priceCurrency":"EUR"},"floorSize":{"value":80},"address":{"addressLocality":"Milano"}}</script>',url
    monkeypatch.setattr(SafeFetcher,'browse',browse)
    found=await service.browse(rid,'web','')
    assert found['refresh_urls']==[]
    assert [c['url'].rsplit('/',1)[1] for c in found['candidates']]==['new','recent']
    for key in ['recent','closed']:
        assert (await service.acquire(rid,f'https://catalog.example/listing/{key}'))['already_known']
    assert (await service.acquire(rid,'https://catalog.example/listing/new'))['new']
    assert len(seen)==2
    assert service.update_progress(rid,agent)['processed']==1

async def test_verified_browser_without_relevant_new_candidates_completes(browser_online,monkeypatch):
    service,rid=browser_online
    async def browse(self,url):return '<a href="/listing/outside-budget">Fuori budget</a>',url
    monkeypatch.setattr(SafeFetcher,'browse',browse)
    await service.browse(rid,'web','')
    result=await service.complete(rid)
    assert result['pending']==0 and result['stats']['processed']==0
    service.db.execute('UPDATE runs SET analysis_done=1 WHERE id=?',(rid,))
    service.engine.finish(rid)
    assert service.db.one('SELECT status FROM runs WHERE id=?',(rid,))['status']=='completed'

async def test_listing_known_only_to_other_agent_can_be_acquired(online,monkeypatch):
    from app.schemas import Listing
    from app.services.store import upsert_listing
    service,rid=online
    p=Listing(listing_key='shared',url='https://catalog.example/listing/shared',title='Shared',
              city='Milano',price=550000,surface=80,currency='EUR',transaction_type='sale')
    pid,_,_=upsert_listing(service.db,service.settings,'web',p)
    async def fetch(self,url):
        if url.endswith('/search'):return '<a href="/listing/shared">Shared</a>',url
        return '<script type="application/ld+json">{"@type":"Apartment","name":"Shared","offers":{"price":550000,"priceCurrency":"EUR"},"floorSize":{"value":80},"address":{"addressLocality":"Milano"}}</script>',url
    monkeypatch.setattr(SafeFetcher,'get',fetch)
    await service.search(rid)
    result=await service.acquire(rid,p.url)
    assert 'already_known' not in result
    assert service.db.one("SELECT property_id FROM agent_properties WHERE agent_id='agent-milano' AND property_id=?",(pid,))
