import pytest
from app.db import dump,now
from app.services.source_probe import probe
from app.connectors.safe_http import SafeFetcher,SourceBlocked


def source(db,**config):
    cfg={'search_url':'https://catalog.example.test/{city}', 'listing_selector':'a',
         'listing_url_pattern':'/p/', 'fields':{}, 'probe_city':'Como',**config}
    db.execute("INSERT INTO sources(id,name,kind,domain,config,permission_at,created_at) VALUES('s','Test','html','catalog.example.test',?,?,?)",(dump(cfg),now(),now()))
    return db.one("SELECT * FROM sources WHERE id='s'")


@pytest.mark.asyncio
async def test_probe_never_assumes_milano(db,settings,monkeypatch):
    row=source(db,probe_city='')
    async def no_request(*a):
        raise AssertionError('No network allowed before explicit city')
    monkeypatch.setattr(SafeFetcher,'get',no_request)
    with pytest.raises(ValueError,match='comune'):
        await probe(db,settings,row)


@pytest.mark.asyncio
async def test_probe_saves_sample_not_properties(db,settings,monkeypatch):
    row=source(db)
    urls=[]
    async def fetch(self,url):
        urls.append(url)
        self.request_count+=1
        if len(urls)==1:return '<a href="/p/1">Immobile</a>',url
        return '''<script type="application/ld+json">{"@type":"Apartment","name":"Test",
          "description":"Annuncio di test controllato", "floorSize":{"value":100},
          "offers":{"price":100000,"priceCurrency":"EUR"}}</script>''',url
    monkeypatch.setattr(SafeFetcher,'get',fetch)
    result=await probe(db,settings,row)
    assert result['ok'] and result['links_found']==1 and len(urls)==2
    assert urls[0].endswith('/como')
    assert not db.all('SELECT * FROM properties')
    assert db.one('SELECT report FROM source_probes')


@pytest.mark.asyncio
async def test_block_pauses_probe_and_does_not_retry(db,settings,monkeypatch):
    row=source(db)
    calls=[]
    async def blocked(*args):
        calls.append(1)
        raise SourceBlocked('HTTP 429',retry_after=180)
    monkeypatch.setattr(SafeFetcher,'get',blocked)
    assert not (await probe(db,settings,row))['ok']
    with pytest.raises(ValueError,match='pausa'):
        await probe(db,settings,row)
    assert len(calls)==1
    assert db.one('SELECT status FROM sources')['status']=='blocked'
