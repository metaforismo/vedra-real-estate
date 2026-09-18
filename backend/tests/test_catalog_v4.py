"""Full-archive behavior, collaborative revisions and immutable observed fields."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import dump, load, now, uid
from app.main import create_app
from app.schemas import Listing
from app.services.store import refresh_analysis, upsert_listing


@pytest.fixture
def workspace(tmp_path):
    settings = Settings(data_dir=tmp_path, scheduler=False, worker_enabled=False,
                        admin_password='controlled-test-password-123', allowed_hosts=['testserver'])
    app = create_app(settings)
    with TestClient(app) as c:
        logged = c.post('/api/auth/login', json={
            'email':settings.admin_email, 'password':settings.admin_password}).json()
        c.headers['X-CSRF-Token'] = logged['csrf']
        db = app.state.db
        sid = uid()
        db.execute("INSERT INTO sources(id,name,kind,created_at) VALUES(?,?,'import',?)",
                   (sid, 'Controlled catalogue fixture', now()))
        listings = [Listing(listing_key=str(n), url=f'import://test/{n}', title=f'Ufficio prova {n}',
                    city='Milano', zone='Z1', property_type='office', condition='to_renovate',
                    price=100000+n*10000, surface=100, currency='EUR', transaction_type='sale',
                    area_basis='commercial', description='Ufficio da ristrutturare.') for n in range(5)]
        ids = [upsert_listing(db, settings, sid, p)[0] for p in listings]
        def agent(**extra):
            body = dict(name='Ricerca verificata', city='Milano', runtime='local', source_ids=[sid], criteria={})
            response = c.post('/api/agents', json={**body, **extra})
            assert response.status_code == 201, response.text
            return response.json()['id']
        yield SimpleNamespace(app=app, c=c, db=db, settings=settings, sid=sid, ids=ids,
                              listings=listings, user=logged['user'], agent=agent)


def query(w, **params):
    response = w.c.get('/api/catalog', params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_catalog_defaults_empty_clamp_and_stable_order(workspace):
    w = workspace
    data = query(w)
    assert data['total'] == 5 and len(data['items']) == 5 and data['scope'] == 'full-archive'
    assert query(w, page=100)['page'] == 1
    assert [p['id'] for p in data['items']] == [p['id'] for p in query(w)['items']]
    empty = query(w, city='Assente', page=8)
    assert (empty['page'],empty['pages'],empty['total'],empty['has_next']) == (1,1,0,False)
    assert all(p['work_version'] == 0 for p in data['items'])


@pytest.mark.parametrize('params', [
    {'page':0}, {'page':1000001}, {'page_size':101}, {'page_size':0}, {'sort':'price;--'},
    {'min_price':1}, {'currency':'EU'}, {'currency':'123'}, {'currency':'€€€'},
    {'currency':'EUR','min_price':200,'max_price':100}, {'min_surface':500,'max_surface':100},
    {'min_surface':-1}, {'max_surface':'NaN'}, {'max_price':'inf','currency':'EUR'},
    {'unknown_parameter':'ignored?'}, {'focus':'sold'}, {'q':'x'*201},
])
def test_query_validation(workspace, params):
    assert workspace.c.get('/api/catalog', params=params).status_code == 422


@pytest.mark.parametrize('literal', ['10%','under_score','bang!','O\'Brien',"' OR 1=1 --"])
def test_search_does_not_interpret_sql_or_wildcards(workspace, literal):
    w = workspace
    w.db.execute('UPDATE properties SET title=? WHERE id=?', ('Precisamente '+literal,w.ids[0]))
    result = query(w, q=literal)
    assert result['total'] == 1 and result['items'][0]['id'] == w.ids[0]


def test_ranges_currency_unknown_values_and_source(workspace):
    w = workspace
    w.db.execute("UPDATE properties SET currency='USD' WHERE id=?", (w.ids[0],))
    w.db.execute('UPDATE properties SET price=NULL WHERE id=?', (w.ids[1],))
    result = query(w, currency='eur', min_price=100000, max_price=130000, min_surface=90, max_surface=100)
    assert {p['id'] for p in result['items']} == {w.ids[2],w.ids[3]}
    assert query(w, source_id='absent')['total'] == 0
    assert query(w, source_id=w.sid)['total'] == 5
    assert w.c.get('/api/catalog/facets').json()['currencies'] == ['EUR','USD']


def test_qualification_must_belong_to_selected_agent(workspace):
    w = workspace
    a, b = w.agent(), w.agent(name='Seconda ricerca')
    w.db.execute('INSERT INTO agent_properties VALUES(?,?,?,?,?)', (a,w.ids[0],0,'[]',None))
    w.db.execute('INSERT INTO agent_properties VALUES(?,?,?,?,?)', (b,w.ids[0],1,'[]',None))
    assert query(w, agent_id=a, qualified=True)['total'] == 0
    data = query(w, agent_id=b, qualified=True)
    assert data['total'] == 1
    assert {p['id'] for p in data['items'][0]['search_matches']} == {a,b}
    assert query(w, qualified=True)['total'] == 1


def test_strategy_projection_tracks_analysis_and_observations(workspace):
    w = workspace
    assert query(w, strategy='value_add')['total'] == 5
    prior = load(w.db.one('SELECT analysis FROM properties WHERE id=?',(w.ids[0],))['analysis'])
    refresh_analysis(w.db,w.ids[0],{**prior,'strategies':[{'strategy':'core_plus','evidence':'Test interno.'}]})
    assert query(w,strategy='core_plus')['items'][0]['id'] == w.ids[0]
    assert query(w,strategy='value_add')['total'] == 4
    upsert_listing(w.db,w.settings,w.sid,w.listings[0].model_copy(update={'description':'Descrizione senza strategia.'}))
    assert query(w,strategy='core_plus')['total'] == 0


def test_migration_backfills_current_strategies_not_historical_values(workspace):
    w = workspace
    w.db.execute('DROP TABLE observation_values')
    w.db.execute('DROP TABLE property_strategies')
    w.db.execute('DELETE FROM schema_migrations WHERE version=4')
    w.db.initialize();w.db.initialize()
    assert query(w,strategy='value_add')['total'] == 5
    assert w.db.one('SELECT COUNT(*) n FROM observation_values')['n'] == 0
    assert w.db.one('SELECT COUNT(*) n FROM schema_migrations WHERE version=4')['n'] == 1


def test_focus_slices_are_observed_not_predictions(workspace):
    w = workspace
    old = (datetime.now(timezone.utc)-timedelta(days=10)).isoformat()
    w.db.execute('UPDATE properties SET last_seen=?,first_seen=? WHERE id=?', (old,old,w.ids[0]))
    w.db.execute("INSERT INTO deal_work(property_id,due_date,updated_at,version,updated_by) VALUES(?,?,?,0,?)",
                 (w.ids[1],'2020-01-01',now(),w.user['id']))
    w.db.execute("UPDATE properties SET review_status='acquired' WHERE id=?",(w.ids[2],))
    assert query(w,focus='stale')['items'][0]['id'] == w.ids[0]
    assert query(w,focus='new')['total'] == 4
    assert query(w,focus='unbenchmarked')['total'] == 5
    assert query(w,focus='overdue')['items'][0]['id'] == w.ids[1]
    assert query(w,focus='unassigned')['total'] == 4


def test_legacy_demo_never_leaks(workspace):
    w = workspace
    w.db.execute("UPDATE properties SET is_demo=1,city='HiddenCity' WHERE id=?",(w.ids[0],))
    assert query(w)['total'] == 4
    assert w.c.get('/api/catalog/facets').json()['cities'] == ['Milano']
    assert w.c.post('/api/catalog/selection',json={'ids':[w.ids[0]]}).status_code == 409
    assert w.c.get(f'/api/properties/{w.ids[0]}/history').status_code == 404


def test_archive_beyond_two_thousand_is_searchable_and_exportable(workspace):
    w = workspace
    template = w.db.one('SELECT * FROM properties WHERE id=?',(w.ids[0],))
    columns = list(template)
    insert = 'INSERT INTO properties('+','.join(columns)+') VALUES('+','.join('?' for _ in columns)+')'
    with w.db.transaction() as con:
        for n in range(2001):
            p={**template,'id':f'archive-{n:04}','listing_key':f'archive-{n}',
               'title':f'Immobile archivio {n}', 'city':'Como' if n==2000 else 'Milano',
               'first_seen':'2020-01-01T00:00:00+00:00','last_seen':'2020-01-01T00:00:00+00:00'}
            con.execute(insert,tuple(p[key] for key in columns))
    data = query(w, q='archivio 2000')
    assert data['total'] == 1 and data['items'][0]['id'] == 'archive-2000'
    assert 'Como' in w.c.get('/api/catalog/facets').json()['cities']
    pages = [query(w,page=n,page_size=100) for n in range(1,22)]
    returned = [p['id'] for page in pages for p in page['items']]
    assert len(returned)==len(set(returned))==2006
    assert pages[-1]['page']==21 and len(pages[-1]['items'])==6
    for endpoint,body in [('/api/export',{'format':'csv','ids':['archive-2000']}),
                           ('/api/catalog/export',{'format':'csv','filters':{'q':'archivio 2000'}})]:
        response = w.c.post(endpoint,json=body)
        assert response.status_code == 200,response.text
        assert 'Immobile archivio 2000' in response.text
    response=w.c.post('/api/catalog/export',json={'format':'csv','filters':{}})
    assert response.status_code==422 and 'troncata' in response.text
    assert w.c.get('/api/export/csv').status_code==422
    response=w.c.post('/api/catalog/export',json={'format':'csv','filters':{'city':'Como'}})
    assert response.headers['X-Vedra-Export-Count']=='1'


def test_selection_order_and_validation(workspace):
    w=workspace
    chosen=[w.ids[3],w.ids[0]]
    assert [p['id'] for p in w.c.post('/api/catalog/selection',json={'ids':chosen}).json()['items']]==chosen
    for invalid in ([],[w.ids[0]]*2,['a'*101],[str(n) for n in range(101)]):
        assert w.c.post('/api/catalog/selection',json={'ids':invalid}).status_code==422
    assert w.c.post('/api/catalog/selection',json={'ids':['deleted']}).status_code==409


def test_bulk_review_atomic_conflict_and_preservation(workspace):
    w=workspace
    work={'version':0,'stage':'reviewing','owner_id':w.user['id'],'due_date':'2030-01-01','checklist':{'source_checked':True}}
    assert w.c.put(f'/api/properties/{w.ids[1]}/work',json=work).status_code==200
    items=[{'id':ident,'version':0} for ident in w.ids[:2]]
    response=w.c.post('/api/catalog/review',json={'items':items,'stage':'shortlisted','note':'Esame preliminare.'})
    assert response.status_code==409
    assert w.db.one('SELECT review_status FROM properties WHERE id=?',(w.ids[0],))['review_status']=='new'
    assert w.db.one("SELECT COUNT(*) n FROM audit_log WHERE action='deal.bulk_review'")['n']==0
    assert w.db.one('SELECT COUNT(*) n FROM notes')['n']==0
    items[1]['version']=1
    response=w.c.post('/api/catalog/review',json={'items':items,'stage':'shortlisted','note':'Esame preliminare.'})
    assert response.json()['count']==2
    read=w.c.get(f'/api/properties/{w.ids[1]}/work').json()
    assert read['version']==2 and read['owner_id']==w.user['id'] and read['checklist']['source_checked']
    assert read['due_date']=='2030-01-01'
    assert w.db.one('SELECT COUNT(*) n FROM notes')['n']==2
    assert w.c.post('/api/catalog/review',json={'items':items,'stage':'shortlisted'}).status_code==409


def test_bulk_discard_requires_reason_and_noop_is_not_a_revision(workspace):
    w=workspace
    body={'items':[{'id':w.ids[0],'version':0}],'stage':'discarded'}
    assert w.c.post('/api/catalog/review',json=body).status_code==422
    assert w.c.post('/api/catalog/review',json={**body,'note':'    '}).status_code==422
    assert w.c.post('/api/catalog/review',json={**body,'stage':'new'}).json()['count']==0
    assert w.db.one('SELECT * FROM deal_work WHERE property_id=?',(w.ids[0],)) is None
    assert w.c.post('/api/catalog/review',json={**body,'note':'  Fuori perimetro  '}).json()['count']==1
    assert w.db.one('SELECT body FROM notes')['body']=='Fuori perimetro'


def test_bulk_rejects_duplicate_refs_and_missing_property(workspace):
    w=workspace
    ref={'id':w.ids[0],'version':0}
    assert w.c.post('/api/catalog/review',json={'items':[ref,ref],'stage':'new'}).status_code==422
    assert w.c.post('/api/catalog/review',json={'items':[ref,{'id':'deleted','version':0}],'stage':'reviewing'}).status_code==409
    assert query(w)['items'][0]['work_version']==0


def test_catalog_auth_viewer_and_csrf(workspace):
    w=workspace
    ref={'items':[{'id':w.ids[0],'version':0}],'stage':'reviewing'}
    with TestClient(w.app) as other:
        assert other.get('/api/catalog').status_code==401
    w.db.execute("UPDATE users SET role='viewer' WHERE id=?",(w.user['id'],))
    assert w.c.get('/api/catalog').status_code==200
    assert w.c.post('/api/catalog/review',json=ref).status_code==403
    assert w.c.post('/api/catalog/export',json={'format':'csv','filters':{}}).status_code==200
    del w.c.headers['X-CSRF-Token']
    assert w.c.post('/api/catalog/selection',json={'ids':w.ids[:2]}).status_code==403


def test_saved_views_keep_new_ranges_and_remain_personal(workspace):
    w=workspace
    filters={'currency':'EUR','min_price':100000,'max_price':120000,'focus':'unassigned','sort':'newest'}
    response=w.c.post('/api/saved-views',json={'name':'Budget operativo','filters':filters})
    assert response.status_code==201
    saved=w.c.get('/api/operations').json()['saved_views'][0]['filters']
    assert all(saved[k]==v for k,v in filters.items())
    assert query(w,**{k:v for k,v in saved.items() if v is not None})['total']==3


def test_field_history_records_changes_not_current_reconstruction(workspace):
    w=workspace;pid=w.ids[0]
    first=w.c.get(f'/api/properties/{pid}/history').json()
    assert first['total']==1 and first['with_fields']==1
    assert first['items'][0]['baseline'] and not first['items'][0]['comparable']
    changed=w.listings[0].model_copy(update={'price':95000,'condition':'good','surface':105,'address':'Via esempio 1'})
    upsert_listing(w.db,w.settings,w.sid,changed)
    upsert_listing(w.db,w.settings,w.sid,changed)
    data=w.c.get(f'/api/properties/{pid}/history').json()
    assert data['total']==2
    fields={x['field']:x for x in data['items'][0]['changes']}
    assert fields['price']=={'field':'price','before':100000,'after':95000}
    assert fields['condition']['before']=='to_renovate' and fields['surface']['after']==105
    # Current-row corrections cannot alter a previously observed evidence entry.
    w.db.execute('UPDATE properties SET price=500000 WHERE id=?',(pid,))
    assert w.c.get(f'/api/properties/{pid}/history').json()==data


def test_history_cursor_scoping_and_diff_across_page_boundary(workspace):
    w=workspace;pid=w.ids[0]
    for value in [90000,80000,70000]:
        upsert_listing(w.db,w.settings,w.sid,w.listings[0].model_copy(update={'price':value}))
    first=w.c.get(f'/api/properties/{pid}/history?limit=2').json()
    assert len(first['items'])==2 and first['next_cursor']
    assert next(x for x in first['items'][1]['changes'] if x['field']=='price')['before']==90000
    second=w.c.get(f'/api/properties/{pid}/history',params={'limit':2,'before':first['next_cursor']}).json()
    assert len(second['items'])==2 and second['next_cursor'] is None
    assert not {i['id'] for i in first['items']}&{i['id'] for i in second['items']}
    assert w.c.get(f'/api/properties/{w.ids[1]}/history',params={'before':first['next_cursor']}).status_code==422
    assert w.c.get(f'/api/properties/{pid}/history?limit=51').status_code==422


def test_legacy_history_stays_unknown(workspace):
    w=workspace;pid=w.ids[0]
    oid=w.db.one('SELECT id FROM observations WHERE property_id=?',(pid,))['id']
    w.db.execute('DELETE FROM observation_values WHERE observation_id=?',(oid,))
    upsert_listing(w.db,w.settings,w.sid,w.listings[0].model_copy(update={'price':90000}))
    data=w.c.get(f'/api/properties/{pid}/history').json()
    assert data['total']==2 and data['with_fields']==1
    assert not any(item['changes'] for item in data['items'])
    assert data['items'][0]['has_evidence'] and not data['items'][0]['comparable']


def test_preflight_import_is_not_live_acquisition(workspace):
    w=workspace;aid=w.agent()
    data=w.c.get(f'/api/agents/{aid}/preflight').json()
    assert data['can_enqueue'] and not data['can_run_now']
    assert any('non trova nuovi' in warning for warning in data['sources'][0]['warnings'])
    w.db.execute('INSERT INTO worker_status VALUES(?,?,?,?,?)',('primary','test',now(),now(),0))
    assert w.c.get(f'/api/agents/{aid}/preflight').json()['can_run_now']
    assert w.c.post(f'/api/agents/{aid}/run').status_code==202
    again=w.c.get(f'/api/agents/{aid}/preflight').json()
    assert again['active_run']['status']=='queued'


def test_preflight_blocks_empty_disabled_and_missing_runtime(workspace):
    w=workspace;aid=w.agent()
    w.db.execute('UPDATE sources SET enabled=0 WHERE id=?',(w.sid,))
    assert not w.c.get(f'/api/agents/{aid}/preflight').json()['can_enqueue']
    assert w.c.post(f'/api/agents/{aid}/run').status_code==409
    w.db.execute('UPDATE sources SET enabled=1 WHERE id=?',(w.sid,))
    w.db.execute("UPDATE agents SET runtime='llm' WHERE id=?",(aid,))
    assert not w.c.get(f'/api/agents/{aid}/preflight').json()['can_enqueue']
    assert w.settings.admin_password not in w.c.get(f'/api/agents/{aid}/preflight').text
    assert w.c.get('/api/agents/unknown/preflight').status_code==404


def test_preflight_html_permission_browser_and_cooldown(workspace, monkeypatch):
    w=workspace;aid=w.agent()
    # The preflight must not invoke an HTTP client or a model.
    import httpx
    def no_request(*args,**kwargs):
        raise AssertionError('preflight made a network request')
    monkeypatch.setattr(httpx.AsyncClient,'request',no_request)
    w.db.execute("UPDATE sources SET kind='html',domain='catalog.example',config=? WHERE id=?",
                 (dump({'render_js':True}),w.sid))
    src=w.c.get(f'/api/agents/{aid}/preflight').json()['sources'][0]
    assert len(src['blockers'])==3
    w.settings.live_domains=['catalog.example'];w.settings.browser_enabled=True
    w.db.execute('UPDATE sources SET permission_at=?,permission_note=? WHERE id=?',(now(),'Accordo test autorizzato',w.sid))
    data=w.c.get(f'/api/agents/{aid}/preflight').json()
    assert data['can_enqueue'] and data['sources'][0]['warnings']
    later=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
    w.db.execute('INSERT INTO source_health(source_id,next_retry) VALUES(?,?)',(w.sid,later))
    assert not w.c.get(f'/api/agents/{aid}/preflight').json()['can_enqueue']
    w.db.execute('UPDATE source_health SET next_retry=? WHERE source_id=?',('invalid',w.sid))
    assert not w.c.get(f'/api/agents/{aid}/preflight').json()['can_enqueue']


def test_source_edit_invalidates_old_probe_but_preserves_backoff(workspace):
    w=workspace
    body={'name':'Fonte autorizzata','domain':'catalog.example', 'permission_note':'Permesso test documentato',
          'permission_confirmed':True, 'config':{'search_url':'https://catalog.example/{city}/'}}
    sid=w.c.post('/api/sources',json=body).json()['id']
    w.db.execute('INSERT INTO source_probes VALUES(?,?,?)',(sid,now(),dump({'ok':True})))
    w.db.execute('INSERT INTO source_health(source_id,next_retry) VALUES(?,?)',(sid,'2030-01-01T00:00:00+00:00'))
    edited=w.c.put(f'/api/sources/{sid}',json={**body,'name':'Fonte riconfigurata'})
    assert edited.status_code==200,edited.text
    assert w.db.one('SELECT * FROM source_probes WHERE source_id=?',(sid,)) is None
    assert w.db.one('SELECT next_retry FROM source_health WHERE source_id=?',(sid,))['next_retry']=='2030-01-01T00:00:00+00:00'


def test_archived_metadata_copies_to_a_clean_database(workspace, tmp_path):
    from app.db import Database
    import importlib.util
    from pathlib import Path
    path=Path(__file__).resolve().parents[2]/'scripts/migrate_sqlite.py'
    spec=importlib.util.spec_from_file_location('v4_transfer',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    target=Database(tmp_path/'target.sqlite3');target.initialize()
    counts=module.copy_rows(workspace.db,target)
    assert counts['observation_values']==5
    assert counts['property_strategies']==workspace.db.one('SELECT COUNT(*) n FROM property_strategies')['n']
    assert target.one('SELECT COUNT(*) n FROM sessions')['n']==0
    with pytest.raises(ValueError,match='non vuoto'):
        module.copy_rows(workspace.db,target)
    assert target.one('SELECT COUNT(*) n FROM observation_values')['n']==5


def test_current_analysis_update_never_changes_historical_evidence(workspace):
    w=workspace;pid=w.ids[0]
    before=w.c.get(f'/api/properties/{pid}/history').json()
    refresh_analysis(w.db,pid,{'summary':'Altra lettura', 'strategies':[], 'caveats':[], 'engine':'local'})
    assert w.c.get(f'/api/properties/{pid}/history').json()==before


def test_currency_change_is_preserved_in_history(workspace):
    w=workspace;pid=w.ids[0]
    upsert_listing(w.db,w.settings,w.sid,w.listings[0].model_copy(update={'currency':'USD','price':90000}))
    item=w.c.get(f'/api/properties/{pid}/history').json()['items'][0]
    assert item['price_context']['currency']=='USD'
    assert item['previous_price_context']['currency']=='EUR'
    assert {x['field'] for x in item['changes']}=={'price','currency'}
