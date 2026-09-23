"""Behavioral tests for the operational workspace, not UI-only placeholders."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.config import Settings
from app.db import dump, now, uid
from app.schemas import Listing
from app.services.engine import Engine
from app.services.store import upsert_listing
from app.services.operations import notify


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    async def no_loop(self):
        pass
    monkeypatch.setattr(Engine, 'loop', no_loop)
    settings = Settings(data_dir=tmp_path, scheduler=False, worker_enabled=False,
                        admin_password='local-test-password-123', allowed_hosts=['testserver'])
    app = create_app(settings)
    with TestClient(app) as client:
        logged = client.post('/api/auth/login', json={
            'email':settings.admin_email, 'password':settings.admin_password}).json()
        client.headers['X-CSRF-Token'] = logged['csrf']
        db = app.state.db
        sid = uid()
        db.execute("INSERT INTO sources(id,name,kind,created_at) VALUES(?,?,'import',?)",(sid,'Synthetic controlled test',now()))
        ids=[]
        for n in range(5):
            listing=Listing(listing_key=str(n), url=f'import://test/{n}', title=f'Test {n}',
                city='Milano',zone='Z1',property_type='office',condition='to_renovate',
                price=100000+n*10000,surface=100,currency='EUR',transaction_type='sale',
                area_basis='commercial',description='Ufficio da ristrutturare.',is_demo=False)
            ids.append(upsert_listing(db,settings,sid,listing)[0])
        yield app,client,settings,ids,logged['user']


def test_new_install_empty_before_explicit_import(settings):
    assert not hasattr(Settings(data_dir=settings.data_dir),'seed_demo')


def test_deal_revision_conflict_and_legacy_patch(workspace):
    app,c,s,ids,user=workspace
    url=f'/api/properties/{ids[0]}/work'
    assert c.get(url).json()['version']==0
    body={'version':0,'owner_id':user['id'],'stage':'due_diligence','due_date':'2026-12-01',
          'checklist':{'source_checked':True}}
    assert c.put(url,json=body).json()['version']==1
    assert c.put(url,json=body).status_code==409
    saved=c.get(url).json()
    assert saved['checklist']['source_checked'] and saved['due_date']=='2026-12-01'
    assert c.patch(f'/api/properties/{ids[0]}',json={'review_status':'negotiation'}).status_code==200
    assert c.put(url,json={**body,'version':1}).status_code==409
    assert app.state.db.one('SELECT review_status FROM properties WHERE id=?',(ids[0],))['review_status']=='negotiation'


def test_revision_rejects_unknown_owner(workspace):
    _,c,_,ids,_=workspace
    assert c.put(f'/api/properties/{ids[0]}/work',json={'version':0,'owner_id':'missing'}).status_code==422


def test_scenario_save_reload_delete(workspace):
    _,c,_,ids,_=workspace
    body={'name':'Scenario test','inputs':{'purchase':100000,'sale':160000,'works':20000,
        'acquisition_costs':10000,'contingency_pct':10,'selling_pct':3,'holding_monthly':100,'months':12}}
    result=c.post('/api/scenarios/calculate',json=body).json()
    assert result['invested']==133200 and result['profit']==22000
    assert len(result['sensitivity'])==6
    assert result['roi_pct']==16.52
    saved=c.post(f'/api/properties/{ids[0]}/scenarios',json=body)
    assert saved.status_code==201
    read=c.get(f'/api/properties/{ids[0]}/scenarios').json()
    assert len(read)==1 and read[0]['result']==result
    assert c.delete('/api/scenarios/'+saved.json()['id']).status_code==200
    assert c.get(f'/api/properties/{ids[0]}/scenarios').json()==[]


@pytest.mark.parametrize('bad', [{'sale':0},{'purchase':-1},{'months':0},{'selling_pct':100},{'works':-10}])
def test_scenario_rejects_invalid_inputs(workspace,bad):
    _,c,_,_,_=workspace
    assert c.post('/api/scenarios/calculate',json={'inputs':{'purchase':100,'sale':200,**bad}}).status_code==422


def test_scenario_requires_eur(workspace):
    app,c,_,ids,_=workspace
    app.state.db.execute("UPDATE properties SET currency='USD' WHERE id=?",(ids[0],))
    assert c.post(f'/api/properties/{ids[0]}/scenarios',json={'inputs':{'purchase':100,'sale':200}}).status_code==422


def test_comparables_exclude_duplicate_asset_and_incompatible_data(workspace):
    app,c,_,ids,_=workspace
    url=f'/api/properties/{ids[0]}/comparables'
    base=c.get(url).json()
    assert len(base['items'])==4 and base['median_sqm']==1250
    assert c.post('/api/duplicates/review',json={'a':ids[0],'b':ids[1],'decision':'same_asset'}).status_code==200
    assert len(c.get(url).json()['items'])==3
    app.state.db.execute("UPDATE properties SET condition='good' WHERE id=?",(ids[2],))
    smaller=c.get(url).json()
    assert len(smaller['items'])==2 and smaller['median_sqm'] is None
    assert app.state.db.one('SELECT COUNT(*) n FROM properties')['n']==5


def test_comparables_do_not_impute_missing_metadata(workspace):
    app,c,_,ids,_=workspace
    app.state.db.execute("UPDATE properties SET zone='' WHERE id=?",(ids[0],))
    data=c.get(f'/api/properties/{ids[0]}/comparables').json()
    assert data['items']==[] and data['median_sqm'] is None


def test_duplicate_review_refuses_demo_real_mix(workspace):
    app,c,_,ids,_=workspace
    app.state.db.execute('UPDATE properties SET is_demo=1 WHERE id=?',(ids[1],))
    assert c.post('/api/duplicates/review',json={'a':ids[0],'b':ids[1],'decision':'same_asset'}).status_code==404
    assert c.post('/api/duplicates/review',json={'a':ids[0],'b':ids[0],'decision':'distinct'}).status_code==422


def test_views_are_saved_and_removable(workspace):
    _,c,_,_,_=workspace
    response=c.post('/api/saved-views',json={'name':'Milano shortlist','filters':{'city':'Milano','starred':True}})
    assert response.status_code==201
    views=c.get('/api/operations').json()['saved_views']
    assert len(views)==1 and views[0]['filters']['starred']
    assert c.delete('/api/saved-views/'+response.json()['id']).status_code==200
    assert c.get('/api/operations').json()['saved_views']==[]


def test_notifications_idempotent_and_personal(workspace):
    app,c,s,ids,user=workspace
    kwargs=dict(kind='new_property',title='Nuovo',body='Test',dedupe_key='test-event',property_id=ids[0])
    notify(app.state.db,s,**kwargs);notify(app.state.db,s,**kwargs)
    rows=c.get('/api/notifications').json()
    assert len(rows)==1 and rows[0]['read_at'] is None
    assert c.post('/api/notifications/'+rows[0]['id']+'/read').status_code==200
    assert c.get('/api/operations').json()['unread']==0
    assert app.state.db.one('SELECT user_id FROM notification_reads')['user_id']==user['id']


def test_notification_datasets_remain_separate(workspace):
    app,c,s,ids,_=workspace
    notify(app.state.db,s,kind='test',title='Demo',body='Test',dedupe_key='d',is_demo=True)
    assert c.get('/api/notifications?dataset=real').json()==[]
    assert c.get('/api/notifications?dataset=demo').status_code==422
    assert c.get('/api/operations?dataset=invalid').status_code==422


def test_readiness_is_honest_and_no_credentials_in_response(workspace):
    app,c,s,_,_=workspace
    assert c.get('/api/readiness').json()['checks']['worker'] is False
    app.state.db.execute('INSERT INTO worker_status VALUES(?,?,?,?,?)',
        ('primary','test-worker',now(),now(),0))
    result=c.get('/api/readiness').json()
    assert result['checks']['database'] and result['checks']['worker']
    assert result['hermes_verified'] is False
    assert s.admin_password not in c.get('/api/workspace').text
    assert 'ai_key' not in c.get('/api/operations').text


def test_password_revokes_other_sessions(workspace):
    app,c,s,_,user=workspace
    from app.security import create_session
    create_session(app.state.db,user,24)
    assert app.state.db.one('SELECT COUNT(*) n FROM sessions')['n']==2
    assert c.post('/api/auth/password',json={'current_password':'wrong','new_password':'replacement-password-123'}).status_code==403
    response=c.post('/api/auth/password',json={'current_password':s.admin_password,'new_password':'replacement-password-123'})
    assert response.status_code==200
    assert app.state.db.one('SELECT COUNT(*) n FROM sessions')['n']==1
    assert c.get('/api/auth/me').status_code==200
    assert any(x['action']=='user.password_changed' for x in c.get('/api/audit').json())


def test_viewer_cannot_edit_work_or_scenarios(workspace):
    app,c,_,ids,_=workspace
    response=c.post('/api/users',json={'email':'viewer@test.local','name':'Viewer','password':'viewer-password-123','role':'viewer'})
    assert response.status_code==201
    c.post('/api/auth/logout')
    login=c.post('/api/auth/login',json={'email':'viewer@test.local','password':'viewer-password-123'}).json()
    c.headers['X-CSRF-Token']=login['csrf']
    assert c.put(f'/api/properties/{ids[0]}/work',json={'version':0}).status_code==403
    assert c.post(f'/api/properties/{ids[0]}/scenarios',json={'inputs':{'purchase':100,'sale':200}}).status_code==403
    assert c.get('/api/audit').status_code==403
    assert c.get('/api/readiness').status_code==403
    assert c.post('/api/saved-views',json={'name':'Personal'}).status_code==422
    assert c.post('/api/saved-views',json={'name':'Personal','filters':{}}).status_code==201


def test_scoped_hermes_capability_expiry_and_revocation(workspace):
    from app.security import token_hash
    from app.schemas import Criteria
    app,c,_,_,_=workspace
    db=app.state.db
    sid=db.one('SELECT id FROM sources')['id']
    db.execute('INSERT INTO agents VALUES(?,?,?,?,?,?,0,1,NULL,?,?)',
        ('test-hermes','Test','Milano',dump(Criteria().model_dump()),dump([sid]),'hermes',now(),now()))
    run=app.state.engine.enqueue('test-hermes')
    rid=run['id']
    db.execute("UPDATE runs SET status='running' WHERE id=?",(rid,))
    token='0'*64
    expiry=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat(timespec='seconds')
    db.execute('INSERT INTO run_capabilities VALUES(?,?,?)',(rid,token_hash(token),expiry))
    headers={'Authorization':'Bearer run:'+token}
    assert c.get(f'/bridge/runs/{rid}',headers=headers).status_code==200
    assert c.get('/bridge/runs/not-this-run',headers=headers).status_code==401
    assert c.post(f'/bridge/runs/{rid}/collect',headers=headers).status_code==403
    db.execute("UPDATE run_capabilities SET expires_at='2000-01-01T00:00:00+00:00'")
    assert c.get(f'/bridge/runs/{rid}',headers=headers).status_code==401
    db.execute('UPDATE run_capabilities SET expires_at=?',(expiry,))
    app.state.engine.finish(rid,'cancelled')
    assert c.get(f'/bridge/runs/{rid}',headers=headers).status_code==401
    assert db.all('SELECT * FROM run_capabilities')==[]


def test_closed_listings_are_not_current_market_comparables(workspace):
    app,c,_,ids,_=workspace
    app.state.db.execute("UPDATE properties SET availability='sold' WHERE id=?",(ids[1],))
    app.state.db.execute("UPDATE properties SET availability='review' WHERE id=?",(ids[2],))
    res=c.get(f'/api/properties/{ids[0]}/comparables').json()
    assert len(res['items'])==2 and res['median_sqm'] is None
    assert not {ids[1],ids[2]}.intersection(x['id'] for x in res['items'])
