import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.db import Database, SCHEMA, dump, load, now
from app.schemas import Listing, Criteria
from app.security import token_hash
from app.services.engine import Engine
from app.services.llm import ChatModelClient
from app.services.store import upsert_listing
from app.services.operations import source_failed, source_succeeded, notify
from app.services.worker_lock import WorkerLock
from app.connectors.sitemap import sitemap_links


def source(db):
    db.execute("INSERT INTO sources(id,name,kind,created_at) VALUES('source','Controlled import','import',?)",(now(),))


def agent(db,runtime='llm'):
    db.execute('INSERT INTO agents VALUES(?,?,?,?,?,?,0,1,NULL,?,?)',
        ('agent','Controlled test','Milano',dump(Criteria(max_listings=10).model_dump()),dump(['source']),runtime,now(),now()))


def listing(n=0):
    return Listing(listing_key=str(n),url=f'import://test/{n}',title=f'Ufficio {n}',city='Milano',
        price=100000,surface=100,currency='EUR',transaction_type='sale',property_type='office',
        description='Ufficio da ristrutturare.')


def test_version_one_migration_preserves_references(settings):
    old=Database(settings.db_path)
    with old.transaction() as con:
        con.executescript(SCHEMA)
        con.execute('INSERT INTO schema_migrations VALUES(1,?)',(now(),))
    source(old);agent(old,'local')
    old.execute("INSERT INTO runs(id,agent_id,status,trigger,runtime,created_at) VALUES('old-run','agent','completed','manual','local',?)",(now(),))
    old.initialize();old.initialize()
    old.execute("UPDATE agents SET runtime='llm' WHERE id='agent'")
    assert old.one('SELECT agent_id FROM runs')['agent_id']=='agent'
    assert len(old.all('SELECT version FROM schema_migrations'))==5
    assert old.all('PRAGMA foreign_key_check')==[]


def test_observations_only_on_changes(db,settings):
    source(db)
    first=listing()
    pid,created,changed=upsert_listing(db,settings,'source',first,raw='first')
    assert created and changed
    assert upsert_listing(db,settings,'source',first)==(pid,False,False)
    changed_listing=first.model_copy(update={'price':90000})
    assert upsert_listing(db,settings,'source',changed_listing,raw='second')==(pid,False,True)
    assert [r['price'] for r in db.all('SELECT price FROM observations ORDER BY rowid')]==[100000,90000]
    assert db.one('SELECT last_detail_at FROM listing_checks WHERE property_id=?',(pid,))


async def test_direct_runtime_incremental_and_reanalyse_change(db,settings,monkeypatch):
    settings.ai_model='test-model'
    source(db);agent(db)
    record=listing();pid=upsert_listing(db,settings,'source',record)[0]
    calls=[]
    async def classify(self,p):
        calls.append(p)
        return {'summary':'Ufficio da ristrutturare.','strategies':[],'caveats':[],
                'engine':'llm','model':settings.ai_model}, {'input_tokens':100,'output_tokens':20,'estimated_eur':None,'usage_reported':True}
    monkeypatch.setattr(ChatModelClient,'classify',classify)
    engine=Engine(db,settings)
    first=engine.enqueue('agent');await engine.execute(first['id'])
    assert db.one('SELECT status FROM runs WHERE id=?',(first['id'],))['status']=='completed'
    second=engine.enqueue('agent');await engine.execute(second['id'])
    assert len(calls)==1 and db.one('SELECT COUNT(*) n FROM ai_usage')['n']==1
    upsert_listing(db,settings,'source',record.model_copy(update={'description':'Ufficio da ristrutturare, nuova descrizione.'}))
    third=engine.enqueue('agent');await engine.execute(third['id'])
    assert len(calls)==2
    assert db.one('SELECT COUNT(*) n FROM properties')['n']==1


async def test_runtime_budget_defers_without_losing_listings(db,settings,monkeypatch):
    settings.ai_model='test-model';settings.max_ai_listings=1
    source(db);agent(db)
    for n in range(2):upsert_listing(db,settings,'source',listing(n))
    async def classify(self,p):
        return {'summary':'','strategies':[],'engine':'llm','model':'test-model'}, {'input_tokens':None,'output_tokens':None,'estimated_eur':None,'usage_reported':False}
    monkeypatch.setattr(ChatModelClient,'classify',classify)
    e=Engine(db,settings);r=e.enqueue('agent');await e.execute(r['id'])
    assert db.one('SELECT status FROM runs WHERE id=?',(r['id'],))['status']=='partial'
    assert db.one('SELECT COUNT(*) n FROM properties')['n']==2
    assert db.one('SELECT COUNT(*) n FROM semantic_tasks WHERE submitted=0')['n']==1
    r2=e.enqueue('agent');await e.execute(r2['id'])
    assert db.one('SELECT status FROM runs WHERE id=?',(r2['id'],))['status']=='completed'
    assert db.one('SELECT COUNT(*) n FROM ai_usage')['n']==2


def test_os_worker_lock_exclusive_and_released(tmp_path):
    a=WorkerLock(tmp_path/'worker.lock');b=WorkerLock(tmp_path/'worker.lock')
    a.acquire()
    try:
        with pytest.raises(RuntimeError):b.acquire()
    finally:a.release()
    b.acquire();b.release()


def test_cooldown_retains_error_until_success(db):
    source(db)
    source_failed(db,'source','Rate limited',retry_after=3600)
    state=db.one('SELECT * FROM source_health')
    assert state['failures']==1
    assert datetime.fromisoformat(state['next_retry'])>datetime.now(timezone.utc)+timedelta(minutes=59)
    source_failed(db,'source','Again')
    assert db.one('SELECT failures FROM source_health')['failures']==2
    source_succeeded(db,'source',requests=2)
    state=db.one('SELECT * FROM source_health')
    assert state['failures']==0 and state['next_retry'] is None and state['requests']==2


def test_demo_notifications_never_send_mail(db,settings):
    settings.mail_enabled=True;settings.smtp_recipients=['test@example.invalid']
    notify(db,settings,kind='test',title='Demo',body='Synthetic',dedupe_key='demo',is_demo=True)
    assert db.all('SELECT * FROM mail_outbox')==[]
    notify(db,settings,kind='test',title='Real event',body='Synthetic test event',dedupe_key='real')
    notify(db,settings,kind='test',title='Real event',body='Synthetic test event',dedupe_key='real')
    assert len(db.all('SELECT * FROM mail_outbox'))==1


def test_sitemap_bounded_unique_and_namespaced():
    text='<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>https://catalog.example/p/{i}</loc></url>' for i in (1,1,2,3))+'</urlset>'
    assert sitemap_links(text,'https://catalog.example',limit=2)==['https://catalog.example/p/1','https://catalog.example/p/2']


@pytest.mark.parametrize('text',['<!DOCTYPE x><urlset/>','<!ENTITY a "b"><urlset/>','<sitemapindex/>','<bad'])
def test_sitemap_rejects_unbounded_or_invalid_formats(text):
    with pytest.raises(ValueError):sitemap_links(text,'https://catalog.example')


async def test_collector_refresh_window_and_price_history(db,settings,monkeypatch):
    from pathlib import Path
    from app.connectors.safe_http import SafeFetcher
    source(db);agent(db,'local')
    config={'search_url':'https://catalog.example/search','listing_url_pattern':'/immobili/',
            'listing_selector':'a[href]','max_pages':1,'detail_refresh_hours':24}
    db.execute("UPDATE sources SET kind='html',domain='catalog.example',permission_at=?,config=? WHERE id='source'",(now(),dump(config)))
    html=(Path(__file__).parent/'fixtures/html/listing.html').read_text()
    calls=[]
    async def fetch(self,url):
        calls.append(url)
        return ('<a href="/immobili/001">Record</a>' if url.endswith('/search') else html),url
    monkeypatch.setattr(SafeFetcher,'get',fetch)
    engine=Engine(db,settings)
    first=engine.enqueue('agent');await engine.execute(first['id'])
    assert len(calls)==2
    assert db.one('SELECT COUNT(*) n FROM properties')['n']==1
    old_seen=db.one('SELECT last_seen FROM properties')['last_seen']
    second=engine.enqueue('agent');await engine.execute(second['id'])
    assert len(calls)==3
    assert db.one('SELECT last_seen FROM properties')['last_seen']==old_seen
    assert load(db.one('SELECT stats FROM runs WHERE id=?',(second['id'],))['stats'])['cached']==1
    db.execute("UPDATE listing_checks SET last_detail_at='2000-01-01T00:00:00+00:00'")
    html=html.replace('600000','550000')
    third=engine.enqueue('agent');await engine.execute(third['id'])
    assert len(calls)==5
    assert db.one('SELECT price FROM properties')['price']==550000
    assert db.one('SELECT COUNT(*) n FROM observations')['n']==2
    assert db.one('SELECT requests FROM source_health')['requests']==5
