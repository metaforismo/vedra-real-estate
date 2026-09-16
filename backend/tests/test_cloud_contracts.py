import importlib.util
import json
from pathlib import Path

import pytest

from app.config import Settings
from app.db_drivers import PostgresDriver, postgres_query
from app.services.media import raster_type

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('build_vercel',ROOT/'scripts/build_vercel.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize('sql,want', [
    ('SELECT ?','SELECT %s'),
    ("SELECT '?' AS literal, ?", "SELECT '?' AS literal, %s"),
    ("SELECT 'l''immobile ?' WHERE id=?", "SELECT 'l''immobile ?' WHERE id=%s"),
    ("SELECT x FROM y WHERE name LIKE '%?%' AND id=?", "SELECT x FROM y WHERE name LIKE '%%?%%' AND id=%s"),
    ('SELECT 5 % 2, ?', 'SELECT 5 %% 2, %s'),
])
def test_parameter_translation(sql,want):
    assert postgres_query(sql)==want


@pytest.mark.parametrize('schema',['public','auth','storage','realtime','unsafe; DROP TABLE users','name"quoted'])
def test_private_schema_validation_before_driver_import(schema):
    with pytest.raises(ValueError):
        PostgresDriver('postgresql://unused',schema,4)


def test_transaction_pooler_rejected():
    with pytest.raises(ValueError,match='session'):
        Settings(database_url='postgresql://user:password@db.example:6543/postgres')


@pytest.mark.parametrize('url',['http://api.example','https://user:pass@api.example','https://api.example/api',
    'https://api.example?token=secret','https://api.example:8443','https://api.example/$1',''])
def test_vercel_origin_validation(tmp_path,url):
    with pytest.raises(ValueError):
        module.build(tmp_path,url)


def test_static_bundle_never_contains_backend_or_secrets(tmp_path):
    for folder in ('frontend/src','frontend/public','backend','data'):
        (tmp_path/folder).mkdir(parents=True)
    (tmp_path/'frontend/index.html').write_text('<html lang="it"></html>')
    (tmp_path/'frontend/src/app.js').write_text('export const version=3;')
    (tmp_path/'.env').write_text('AI_API_KEY=private-value')
    (tmp_path/'backend/private.py').write_text('private')
    out=module.build(tmp_path,'https://api.example.com')
    files=[p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()]
    assert sorted(files)==['config.json','static/assets/app.js','static/index.html']
    routes=json.loads((out/'config.json').read_text())['routes']
    assert any(r.get('status')==404 and 'bridge' in r['src'] for r in routes)
    proxy=next(r for r in routes if r.get('src')=='/api/(.*)')
    assert proxy['dest']=='https://api.example.com/api/$1'
    assert proxy['headers']['Cache-Control']=='no-store'
    assert 'private-value' not in ''.join(p.read_text() for p in out.rglob('*') if p.is_file())


@pytest.mark.parametrize('body,mime',[(b'\x89PNG\r\n\x1a\n','image/png'),(b'\xff\xd8\xfftest','image/jpeg'),
    (b'RIFF0000WEBP','image/webp'),(b'<svg onload="bad()"/>',None),(b'<html>login</html>',None)])
def test_proxy_only_serves_raster_magic(body,mime):
    assert raster_type(body)==mime
