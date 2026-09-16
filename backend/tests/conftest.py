from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.db import Database
from app.services.engine import Engine

ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path,  scheduler=False,worker_enabled=False,
                    admin_password="test-only-password-56891",allowed_hosts=['testserver','localhost','127.0.0.1'],
                    live_domains=['catalog.example'],request_delay=0,
                    bridge_token='test-only-bridge-token',hermes_key='test-only-hermes-key')

@pytest.fixture
def db(settings):
    database=Database(settings.db_path); database.initialize()
    return database

@pytest.fixture(scope='module')
def api(tmp_path_factory):
    from app.main import create_app
    settings=Settings(data_dir=tmp_path_factory.mktemp('api'),scheduler=False,worker_enabled=False,
                      admin_password='test-only-password-56891',allowed_hosts=['testserver','localhost','127.0.0.1'],
                      bridge_token='test-only-bridge-token',hermes_key='test-only-hermes-key')
    patch=pytest.MonkeyPatch()
    async def no_worker(self): pass
    patch.setattr(Engine,'loop',no_worker)
    app=create_app(settings)
    app.state.db.initialize()
    from support.catalog import seed
    seed(app.state.db, settings)
    with TestClient(app) as client:
        login=client.post('/api/auth/login',json={'email':'admin@vedra.local','password':settings.admin_password})
        assert login.status_code==200,login.text
        client.headers['X-CSRF-Token']=login.json()['csrf']
        yield app,client,settings
    patch.undo()
