from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
import pytest
from fastapi import HTTPException
from app.schemas import AgentInput
from app.services.agent_config import revision,save


def payload(**extra):
    return {'name':'Research receipt QA','city':'Milano','source_ids':['demo-milano'],
            'criteria':{'max_price':600000},'interval_minutes':0,'request_id':str(uuid4()),**extra}


def test_create_receipt_replay_and_changed_payload(api):
    app,c,_=api;body=payload()
    first=c.post('/api/agents',json=body)
    assert first.status_code==201,first.text
    replay=c.post('/api/agents',json=body)
    assert replay.json()==first.json()
    assert len(app.state.db.all('SELECT id FROM agents WHERE id=?',(first.json()['id'],)))==1
    changed=c.post('/api/agents',json={**body,'name':'Edited after lost response'})
    assert changed.status_code==409
    assert changed.json()['detail']['agent_id']==first.json()['id']
    assert app.state.db.one('SELECT name FROM agents WHERE id=?',(first.json()['id'],))['name']==body['name']


def test_stale_edit_rejected_and_replay_does_not_reapply(api):
    app,c,_=api;created=c.post('/api/agents',json=payload()).json();ident=created['id']
    edit=payload(name='First operator',expected_revision=created['revision'])
    first=c.put('/api/agents/'+ident,json=edit)
    assert first.status_code==200,first.text
    stale=c.put('/api/agents/'+ident,json=payload(name='Stale operator',expected_revision=created['revision']))
    assert stale.status_code==409
    assert stale.json()['detail']['agent_id']==ident
    second=c.put('/api/agents/'+ident,json=payload(name='Newer configuration',expected_revision=first.json()['revision']))
    assert second.status_code==200
    assert c.put('/api/agents/'+ident,json=edit).json()==first.json()
    assert app.state.db.one('SELECT name FROM agents WHERE id=?',(ident,))['name']=='Newer configuration'


def test_invalid_submission_does_not_consume_key(api):
    app,c,_=api;body=payload(source_ids=['missing-source'])
    assert c.post('/api/agents',json=body).status_code==422
    assert not app.state.db.one('SELECT * FROM agent_write_receipts WHERE request_id=?',(body['request_id'],))
    assert c.post('/api/agents',json={**body,'source_ids':['demo-milano']}).status_code==201


def test_scheduler_timestamp_excluded_but_pause_changes_revision(api):
    app,c,_=api;created=c.post('/api/agents',json=payload()).json();ident=created['id'];db=app.state.db
    db.execute('UPDATE agents SET next_run=? WHERE id=?',('2030-01-01T00:00:00+00:00',ident))
    assert revision(db.one('SELECT * FROM agents WHERE id=?',(ident,)))==created['revision']
    c.post('/api/agents/'+ident+'/toggle')
    assert revision(db.one('SELECT * FROM agents WHERE id=?',(ident,)))!=created['revision']


def test_receipt_cannot_be_replayed_by_other_user(api):
    app,c,_=api;body=payload();c.post('/api/agents',json=body)
    with pytest.raises(HTTPException) as caught:save(app.state.db,AgentInput(**body),'different-user',lambda body,con:None)
    assert caught.value.status_code==409
    assert caught.value.detail['agent_id'] is None


def test_concurrent_edits_have_one_winner(api):
    app,c,_=api;db=app.state.db;created=c.post('/api/agents',json=payload()).json()
    user_id=db.one('SELECT id FROM users LIMIT 1')['id'];gate=Barrier(2)
    def write(name):
        gate.wait()
        try:
            save(db,AgentInput(**payload(name=name,expected_revision=created['revision'])),user_id,lambda body,con:None,created['id'])
            return 200
        except HTTPException as exc:return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(write,['Operator one','Operator two']))
    assert sorted(results)==[200,409]


def test_screen_failure_rolls_back_config_and_receipt(api,monkeypatch):
    app,c,_=api;db=app.state.db;ident='agent-milano';before=db.one('SELECT * FROM agents WHERE id=?',(ident,))
    assert db.one('SELECT * FROM agent_properties WHERE agent_id=?',(ident,))
    def broken(*args):raise RuntimeError('screen failure')
    monkeypatch.setattr('app.services.analysis.screen',broken)
    body=payload(name='Must roll back',expected_revision=revision(before))
    with pytest.raises(RuntimeError,match='screen failure'):
        save(db,AgentInput(**body),db.one('SELECT id FROM users LIMIT 1')['id'],lambda body,con:None,ident)
    assert db.one('SELECT * FROM agents WHERE id=?',(ident,))==before
    assert not db.one('SELECT * FROM agent_write_receipts WHERE request_id=?',(body['request_id'],))


def test_concurrent_create_retry_is_one_write(api):
    app,c,_=api;db=app.state.db;body=AgentInput(**payload());gate=Barrier(2)
    user_id=db.one('SELECT id FROM users LIMIT 1')['id']
    def write(_):
        gate.wait()
        return save(db,body,user_id,lambda body,con:None)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(write,range(2)))
    assert results[0]==results[1]
    db.initialize()
    assert db.one('SELECT response FROM agent_write_receipts WHERE request_id=?',(str(body.request_id),))
