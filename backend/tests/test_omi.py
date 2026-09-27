import json
from datetime import datetime,timezone
import pytest
from app.services.omi import OmiClient,parse_quotes,zone_at,reference_scenarios
from app.connectors.safe_http import SafeFetcher,SourceBlocked
from app.schemas import Listing


def feature(zone='D1',rings=None):
    return {'type':'Feature','properties':{'zona':zone,'descZona':'Test zone'},'geometry':{'type':'Polygon','coordinates':rings or [[[9,45],[10,45],[10,46],[9,46],[9,45]]]}}


def test_geometry_holes_boundaries_and_ambiguity():
    outer=feature()
    assert zone_at([outer],45.5,9.5)[0]['properties']['zona']=='D1'
    assert zone_at([outer],44,9.5) is None
    assert zone_at([outer],45.5,9.00001) is None
    assert zone_at([outer,feature('D2')],45.5,9.5) is None
    hole=[[9.4,45.4],[9.6,45.4],[9.6,45.6],[9.4,45.6],[9.4,45.4]]
    assert zone_at([feature(rings=[hole,*outer['geometry']['coordinates']])],45.5,9.5) is None
    assert zone_at([feature(rings=[hole,*outer['geometry']['coordinates']])],45.8,9.8)


def test_official_table_keeps_type_condition_and_area_basis():
    html='<table><tr>'+''.join('<td>'+x+'</td>' for x in ['Abitazioni civili','Ottimo','3000','4500','L','8','12,5','L'])+'</tr></table>'
    assert parse_quotes(html)==[{'type':'Abitazioni civili','condition':'Ottimo','min_sqm':3000,'max_sqm':4500,'area_basis':'gross'}]
    with pytest.raises(ValueError):parse_quotes('<h1>Service unavailable</h1>')


async def test_network_cache_and_fixed_host(settings,monkeypatch):
    settings.omi_enabled=True;client=OmiClient(settings);calls=[]
    async def get(self,url):
        calls.append(url)
        assert url.startswith('https://www1.agenziaentrate.gov.it/servizi/geopoi_omi/')
        return '[{"PROVINCIA":"MI","DIZIONE":"MILANO"}]',url
    monkeypatch.setattr(SafeFetcher,'get',get)
    assert (await client.provinces())[0]['code']=='MI'
    await client.provinces();assert len(calls)==1
    with pytest.raises(ValueError):await client.cities('http://127.0.0.1')
    with pytest.raises(ValueError):await client.quotes('F205','../../x','20252')
    assert len(calls)==1


async def test_source_failure_does_not_become_a_quote(settings,monkeypatch):
    settings.omi_enabled=True;client=OmiClient(settings)
    async def get(self,url):raise SourceBlocked('rate limit')
    monkeypatch.setattr(SafeFetcher,'get',get)
    with pytest.raises(ValueError,match='non disponibile'):await client.provinces()
    assert not list(client.root.glob('*.json'))


async def test_enrichment_requires_unique_city_and_point(settings,monkeypatch):
    settings.omi_enabled=True;client=OmiClient(settings)
    listing=Listing(title='Test',listing_key='x',url='https://catalog.example/p/1',city='Milano',property_type='residential',latitude=45.5,longitude=9.5)
    monkeypatch.setattr(client,'cached_cities',lambda:[{'code':'F205','name':'MILANO'}])
    async def zones(*args):return [feature()],'20252',{'source_url':'https://www1.agenziaentrate.gov.it/geometry'}
    async def quotes(*args):return {'rows':[],'period':'2025-S2'}
    monkeypatch.setattr(client,'zones',zones);monkeypatch.setattr(client,'quotes',quotes)
    await client.enrich(listing)
    assert listing.zone=='D1' and listing.evidence['market_context']['status']=='available'
    assert 'precision unverified' in listing.evidence['zone']['method']
    listing.longitude=8
    await client.enrich(listing)
    assert listing.evidence['market_context']['status']=='unavailable'


def test_scenarios_are_conditional_and_never_fill_verified_score():
    current=datetime.now(timezone.utc);year=current.year-1
    p={'price':400000,'surface':100,'currency':'EUR','transaction_type':'sale','property_type':'residential','score':None,'discount':None,
       'evidence':{'market_context':{'status':'available','period':f'{year}-S2','rows':[{'type':'Abitazioni civili','condition':'NORMALE','min_sqm':3000,'max_sqm':5000,'area_basis':'gross'}]}}}
    result=reference_scenarios(p);row=result['scenarios'][0]
    assert (row['range_min'],row['range_max'],row['delta_midpoint_pct'])==(300000,500000,0)
    assert row['kind']=='conditional_reference' and row['confidence']=='non_calibrata'
    assert p['score'] is None and p['discount'] is None
    p['evidence']['market_context']['period']='2000-S1'
    assert reference_scenarios(p)['stale'] and not reference_scenarios(p)['scenarios']


def test_omi_endpoints_require_auth(api):
    app,client,settings=api
    from fastapi.testclient import TestClient
    with TestClient(app) as other:
        assert other.get('/api/omi/provinces').status_code==401
    assert client.get('/api/omi/cities?province=../../').status_code==422
