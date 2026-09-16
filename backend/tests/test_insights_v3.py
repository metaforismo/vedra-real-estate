from datetime import datetime, timedelta, timezone

import pytest

from app.db import dump, now, uid
from app.services.insights import market_groups, price_changes, workspace_insights
from app.services.legacy_cleanup import remove
from app.services.worker import worker_health
from app.schemas import Listing, ImportInput
from app.services.imports import import_data
from app.services.store import upsert_listing


def record(n, **values):
    return dict(id=str(n), last_seen='2026-09-16T12:00:00+00:00', city='Milano', zone='Z1',
                property_type='office', condition='good', area_basis='commercial', currency='EUR',
                transaction_type='sale', price=200000+n*1000, surface=100, is_auction=0, **values)


def test_segment_minimum_and_confirmed_duplicates():
    rows = [record(n) for n in range(5)]
    assert market_groups(rows, [])[0]['median_sqm'] == 2020
    merged = market_groups(rows, [{'a':'0', 'b':'1', 'decision':'same_asset'}])[0]
    assert merged['n'] == 4 and merged['median_sqm'] is None
    assert merged['p25_sqm'] is None


@pytest.mark.parametrize('field,value', [('currency','USD'), ('condition','to_renovate'),
    ('transaction_type','rent'), ('zone','Z2'), ('area_basis','net'), ('surface',500)])
def test_segments_never_mix_incompatible_properties(field, value):
    rows = [record(n) for n in range(5)]
    rows[-1][field] = value
    assert all(not g['sufficient'] for g in market_groups(rows, []))


@pytest.mark.parametrize('field', ['zone','condition','area_basis','currency','transaction_type'])
def test_unknown_metadata_does_not_become_a_benchmark(field):
    rows = [record(n) for n in range(10)]
    for row in rows:
        row[field] = ''
    assert market_groups(rows, []) == []


def test_auctions_and_stale_catalog_are_excluded(db):
    rows = [record(n) for n in range(8)]
    for row in rows:
        row['is_auction'] = 1
    assert market_groups(rows, []) == []
    assert workspace_insights(db)['segments'] == []
    assert workspace_insights(db)['archive']['completeness'] is None


def test_price_change_requires_historical_context():
    base = {'property_id':'p','title':'Test','city':'Milano','url':'https://data.example.test/p',
            'observed_at':'2026-09-10','price':200000,'currency':'EUR','transaction_type':'sale',
            'area_basis':'commercial','surface':100}
    lower = {**base, 'price':180000, 'observed_at':'2026-09-11'}
    assert price_changes([base, lower],'2026-09-01')[0]['reduction_pct'] == 10
    for changed in ({'currency':'USD'}, {'surface':99}, {'area_basis':None}):
        assert price_changes([base, {**lower, **changed}], '2026-09-01') == []
    assert price_changes([base,lower],'2026-10-01') == []


def test_observation_context_is_immutable(db,settings):
    db.execute("INSERT INTO sources(id,name,kind,created_at) VALUES('s','Test','import',?)",(now(),))
    p=Listing(listing_key='1',url='https://data.example.test/1',title='Test',price=100000,
              surface=100,currency='EUR',transaction_type='sale',area_basis='commercial')
    pid,_,_=upsert_listing(db,settings,'s',p)
    upsert_listing(db,settings,'s',p.model_copy(update={'price':90000,'surface':90}))
    rows=db.all('SELECT * FROM observation_context ORDER BY surface')
    assert [row['surface'] for row in rows] == [90,100]
    assert workspace_insights(db)['price_reductions'] == []
    db.execute('UPDATE properties SET surface=500 WHERE id=?',(pid,))
    assert [row['surface'] for row in db.all('SELECT * FROM observation_context ORDER BY surface')] == [90,100]


@pytest.mark.parametrize('age,stopping,healthy', [(0,0,True),(50,0,False),(-120,0,False),(0,1,False)])
def test_shared_heartbeat_freshness(db,settings,age,stopping,healthy):
    stamp=(datetime.now(timezone.utc)-timedelta(seconds=age)).isoformat()
    db.execute('INSERT INTO worker_status VALUES(?,?,?,?,?)',('primary','worker',stamp,stamp,stopping))
    assert worker_health(db,settings)['healthy'] is healthy


def test_retired_import_rejected_before_any_write(db,settings):
    with pytest.raises(ValueError,match='dimostrative'):
        import_data(db,settings,ImportInput(kind='csv',content='title,price\nTest,100',is_demo=True,permission_confirmed=True))
    assert not db.all('SELECT * FROM sources')


def test_legacy_cleanup_keeps_real_data_and_is_idempotent(db,settings):
    for sid in ('real','legacy'):
        db.execute('INSERT INTO sources(id,name,kind,created_at) VALUES(?,?,?,?)',
                   (sid,sid,'demo' if sid=='legacy' else 'import',now()))
        upsert_listing(db,settings,sid,Listing(listing_key=sid,url=f'https://data.example.test/{sid}',
                       title=sid,is_demo=sid=='legacy',price=100000,surface=100))
    counts=remove(db)
    assert counts['properties']==1 and counts['sources']==1
    assert db.one('SELECT title FROM properties')['title']=='real'
    assert remove(db)['properties']==0
    assert not db.all('PRAGMA foreign_key_check')


def test_v3_api_hides_retired_data(api):
    app,c,_=api
    pid=app.state.db.one('SELECT id FROM properties')['id']
    app.state.db.execute('UPDATE properties SET is_demo=1 WHERE id=?',(pid,))
    assert c.get('/api/properties/'+pid).status_code==404
    assert c.get('/api/properties/'+pid+'/image').status_code==404
    assert c.get('/api/insights').json()['archive']['total']==35
    app.state.db.execute('UPDATE benchmarks SET is_demo=1')
    assert c.get('/api/benchmarks').json()==[]
