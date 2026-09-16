"""Opt-in integration tests against a disposable database, not a production schema.

Set TEST_DATABASE_URL in CI. Each test owns a random schema and drops only that schema.
"""
import os
from uuid import uuid4

import pytest

from app.config import Settings
from app.db import Database, now
from app.db_drivers import IntegrityError
from app.schemas import Listing
from app.services.insights import workspace_insights
from app.services.store import upsert_listing
from app.services.worker_lock import PostgresWorkerLock

pytestmark=pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='TEST_DATABASE_URL not configured')


@pytest.fixture
def cloud(tmp_path):
    import psycopg
    from psycopg import sql
    url=os.environ['TEST_DATABASE_URL']
    schema='vedra_test_'+uuid4().hex[:12]
    with psycopg.connect(url,autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    settings=Settings(data_dir=tmp_path,database_url=url,database_schema=schema,worker_enabled=False)
    db=Database.from_settings(settings)
    try:
        db.initialize()
        yield db,settings
    finally:
        db.close()
        with psycopg.connect(url,autocommit=True) as admin:
            admin.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def test_postgres_schema_constraints_and_history(cloud):
    db,settings=cloud
    db.initialize()
    assert db.healthy()
    assert [r['version'] for r in db.all('SELECT version FROM schema_migrations ORDER BY version')]==[1,2,3]
    db.execute("INSERT INTO sources(id,name,kind,created_at) VALUES('s','Test 10% ?','import',?)",(now(),))
    p=Listing(listing_key='one',url='https://test.example/1',title='Test',price=250000.25,
              surface=110.15,currency='EUR',transaction_type='sale',area_basis='commercial')
    pid,created,_=upsert_listing(db,settings,'s',p)
    assert created
    upsert_listing(db,settings,'s',p.model_copy(update={'price':240000.25}))
    assert db.one('SELECT COUNT(*) n FROM observation_context')['n']==2
    assert workspace_insights(db)['price_reductions'][0]['property_id']==pid
    with pytest.raises(IntegrityError):
        db.execute("INSERT INTO sources(id,name,kind,created_at) VALUES('s','Duplicate','import',?)",(now(),))
    assert db.one("SELECT name FROM sources WHERE name LIKE ?",('%10% ?',))['name']=='Test 10% ?'


def test_postgres_worker_lock_is_exclusive(cloud):
    db,_=cloud
    first,second=PostgresWorkerLock(db),PostgresWorkerLock(db)
    first.acquire()
    try:
        with pytest.raises(RuntimeError,match='worker'):
            second.acquire()
        first.assert_owned()
    finally:
        first.release()
    second.acquire()
    second.release()


def test_postgres_api_login_and_insights(cloud):
    from fastapi.testclient import TestClient
    from app.main import create_app
    _,settings=cloud
    settings.allowed_hosts=['testserver']
    settings.admin_password='isolated-postgres-test-password'
    app=create_app(settings)
    with TestClient(app) as c:
        response=c.post('/api/auth/login',json={'email':settings.admin_email,'password':settings.admin_password})
        assert response.status_code==200
        c.headers['X-CSRF-Token']=response.json()['csrf']
        assert c.get('/api/workspace').json()['properties']==[]
        assert c.get('/api/insights').json()['archive']['total']==0
        assert c.get('/api/readiness').json()['checks']['worker'] is False
        view=c.post('/api/saved-views',json={'name':'Cloud','filters':{}})
        assert view.status_code==201
