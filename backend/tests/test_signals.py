"""Decision signals stay identical across API lists, daily work and Excel."""
import copy
import io
from datetime import datetime,timedelta,timezone

import pytest
from openpyxl import load_workbook

from app.catalog_schemas import CatalogQuery
from app.db import dump,now
from app.schemas import Listing
from app.services.catalog import by_ids,search
from app.services.decision_facts import dossier
from app.services.exports import export_xlsx
from app.services.market_references import MarketReferences
from app.services.signals import attach_signals
from app.services.store import property_dict,upsert_listing
from app.services.today import queue


def source(db,ident='qa-signals',domain='signals.example'):
    db.execute('INSERT INTO sources(id,name,kind,domain,config,created_at) VALUES(?,?,?,?,?,?)',
               (ident,'QA · Segnali','import',domain,dump({}),now()))


def signal_dataset(db,settings):
    source(db)
    published=datetime.now(timezone.utc)-timedelta(days=10,hours=2)
    omi={'status':'available','period':f'{datetime.now().year}-S1','source_label':'OMI QA','source_url':'https://signals.example/omi',
         'rows':[{'type':'Abitazioni civili','condition':'OTTIMO','min_sqm':4000,'max_sqm':5000,'area_basis':'gross'},
                 {'type':'Abitazioni civili','condition':'SCADENTE','min_sqm':2000,'max_sqm':4000,'area_basis':'commercial'}]}
    contact={'name':'QA Broker','telephone':'+39021234567','email':'qa@signals.example'}
    common={'city':'Milano','zone':'QA Segnali','surface':100,'currency':'EUR','transaction_type':'sale',
            'area_basis':'commercial','property_type':'residential','availability':'listed'}
    listing=Listing(listing_key='subject',url='https://signals.example/subject',title='Vendita diretta dal proprietario',
        description='Categoria catastale C/1. Possibile cambio di destinazione d’uso.',price=300000,condition='to_renovate',
        evidence={'decision_facts':{'published_at':published.isoformat(),'contact':contact},'market_context':omi},**common)
    ident=upsert_listing(db,settings,'qa-signals',listing)[0]
    first=(datetime.now(timezone.utc)-timedelta(days=30,hours=2)).isoformat()
    db.execute('UPDATE properties SET first_seen=?,review_status=? WHERE id=?',(first,'shortlisted',ident))
    for condition,prices in [('to_renovate',(330000,350000,370000)),('renovated',(430000,450000,470000)),('new',(530000,550000,570000))]:
        for n,price in enumerate(prices):
            item=Listing(listing_key=f'{condition}-{n}',url=f'https://signals.example/{condition}/{n}',title=f'{condition} {n}',
                price=price,condition=condition,description='Campione osservato.',**common)
            upsert_listing(db,settings,'qa-signals',item)
    contexts=[(400000,'EUR','sale'),(360000,'EUR','sale'),(350000,'USD','sale'),(340000,'USD','sale'),
              (330000,'USD','rent'),(320000,'USD','rent'),(300000,'EUR','sale')]
    base=datetime.now(timezone.utc)-timedelta(days=7)
    with db.transaction() as con:
        con.execute('DELETE FROM observation_context WHERE observation_id IN (SELECT id FROM observations WHERE property_id=?)',(ident,))
        con.execute('DELETE FROM observation_values WHERE observation_id IN (SELECT id FROM observations WHERE property_id=?)',(ident,))
        con.execute('DELETE FROM observations WHERE property_id=?',(ident,))
        for n,(price,currency,transaction) in enumerate(contexts):
            oid=f'qa-signal-observation-{n}';at=(base+timedelta(hours=n)).isoformat()
            con.execute('INSERT INTO observations VALUES(?,?,?,?,?,?,?)',(oid,ident,at,price,f'hash-{n}',None,'qa'))
            con.execute('INSERT INTO observation_context VALUES(?,?,?,?,?)',(oid,currency,transaction,'commercial',100))
    return ident,published,contexts,base


def full_property(db,ident):
    return property_dict(db.one('SELECT p.*,s.name source_name FROM properties p JOIN sources s ON s.id=p.source_id WHERE p.id=?',(ident,)))


def observed(db,ident):
    return db.all('''SELECT o.property_id,o.observed_at,o.price,c.currency,c.transaction_type FROM observations o
        LEFT JOIN observation_context c ON c.observation_id=o.id WHERE o.property_id=? ORDER BY o.observed_at,o.id''',(ident,))


def test_signal_contract_dates_reductions_contact_refs_and_omi(db,settings):
    ident,published,_,base=signal_dataset(db,settings);p=full_property(db,ident);rows=observed(db,ident)
    references=MarketReferences(db);p['market_references']=references.for_property(p)
    attach_signals(db,[p],references=references,observations={ident:rows});signals=p['signals']
    assert signals['days_listed']==10 and signals['listed_since']==published.date().isoformat() and signals['listed_basis']=='published'
    assert signals['reductions']=={'count':3,'total_pct':-25.0,'from_price':400000,
        'last_at':(base+timedelta(hours=5)).isoformat()}
    assert dossier(p,rows)['price_reductions']==signals['reductions']['count']
    assert 'C/1' in signals['cadastral'] and 'cambio di destinazione' in signals['change_of_use'].casefold()
    assert signals['contact']=={'name':'QA Broker','has_phone':True,'has_email':True,
        'route':'owner_declared','route_label':'Proprietario dichiarato'}
    market=signals['market'];refs={item['key']:item for item in market['refs']}
    assert market['price_sqm']==3000 and market['currency']=='EUR' and market['same_condition_key']=='to_renovate'
    assert [(refs[key]['median_sqm'],refs[key]['delta_pct']) for key in ('to_renovate','renovated','new')]==[(3500,-14.3),(4500,-33.3),(5500,-45.5)]
    assert market['omi']=={'min_sqm':2000.0,'max_sqm':4000.0,'mid_sqm':3000.0,'delta_pct':0.0,
        'period':f'{datetime.now().year}-S1','area_basis':'commercial','stale':False}


@pytest.mark.parametrize('published',[(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),'not-a-date'])
def test_invalid_or_future_published_date_falls_back_and_sparse_or_stale_values_are_null(db,settings,published):
    ident,_,_,_=signal_dataset(db,settings);base=full_property(db,ident);rows=observed(db,ident)
    references=MarketReferences(db);base['market_references']=references.for_property(base);base['observations']=rows
    p=copy.deepcopy(base);p['first_seen']=(datetime.now(timezone.utc)-timedelta(days=8,hours=2)).isoformat()
    p['evidence']['decision_facts']['published_at']=published
    p['market_context']['stale']=True
    p['market_references']['groups'][0]['median_sqm']=None
    attach_signals(db,[p],references=references)
    assert p['signals']['listed_basis']=='first_seen' and p['signals']['days_listed']==8
    assert p['signals']['market']['refs'][0]['delta_pct'] is None
    assert p['signals']['market']['omi']['stale'] and p['signals']['market']['omi']['delta_pct'] is None


def test_catalog_selection_today_reduced_focus_and_listed_sort(db,settings):
    ident,_,_,_=signal_dataset(db,settings)
    page=search(db,CatalogQuery(page_size=100,availability='all',sort='listed'))
    assert page['items'][0]['id']==ident and 'signals' in page['items'][0]
    assert by_ids(db,[ident])[0]['signals']['reductions']['total_pct']==-25.0
    reduced=search(db,CatalogQuery(page_size=100,availability='all',focus='reduced'))
    assert {p['id'] for p in reduced['items']}=={ident}
    today=queue(db);item=next(p for p in today['call']+today['verify'] if p['id']==ident)
    assert item['signals']['market']['refs'][2]['key']=='new'


def test_excel_selection_headers_and_values_match_signals(db,settings):
    ident,_,_,_=signal_dataset(db,settings);p=full_property(db,ident);attach_signals(db,[p])
    sheet=load_workbook(io.BytesIO(export_xlsx([p],db)),data_only=True)['Selezione']
    headers=[cell.value for cell in sheet[1]];values={header:sheet.cell(2,n+1).value for n,header in enumerate(headers)}
    # Price, then the four references with their deltas, then listing age: the order the analyst reads them.
    assert headers[7:23]==['Prezzo/m²','Da ristrutturare /m²','Δ vs Da ristrutturare %','Ristrutturato /m²','Δ vs Ristrutturato %','Nuovo /m²','Δ vs Nuovo %',
        'Campioni (R/Ri/N)','OMI min €/m²','OMI max €/m²','Δ vs OMI medio %','Sconto benchmark %','Giorni sul mercato','Base anzianità','Ribassi osservati','Ribasso totale %']
    assert values['Disponibilità'] in ('Pubblicato','Da verificare','Venduto','Affittato','Ritirato') and values['Fase team']!='new'
    assert values['Prima osservazione'] is None or hasattr(values['Prima osservazione'],'year')
    assert headers.count('Ribassi osservati')==1
    signals=p['signals'];refs={r['key']:r for r in signals['market']['refs']}
    assert values['Giorni sul mercato']==signals['days_listed'] and values['Base anzianità']=='Pubblicazione dichiarata'
    assert values['Ribassi osservati']==signals['reductions']['count'] and values['Ribasso totale %']==signals['reductions']['total_pct']
    assert values['OMI min €/m²']==signals['market']['omi']['min_sqm'] and values['Δ vs OMI medio %']==signals['market']['omi']['delta_pct']
    assert values['Δ vs Nuovo %']==refs['new']['delta_pct'] and values['Campioni (R/Ri/N)']=='3/3/3'


def test_signal_queries_are_batched_and_segment_scaled(db,settings):
    source(db,'qa-query-count','query.example');ids=[]
    for n in range(30):
        listing=Listing(listing_key=f'query-{n}',url=f'https://query.example/{n}',title=f'Query {n}',city='Milano',
            zone='Segmento A' if n<15 else 'Segmento B',property_type='residential',condition=('to_renovate','renovated','new')[n%3],
            price=250000+n*1000,surface=100,area_basis='commercial',currency='EUR',transaction_type='sale',availability='listed')
        ids.append(upsert_listing(db,settings,'qa-query-count',listing)[0])
    items=[full_property(db,ident) for ident in ids]
    class Counter:
        def __init__(self,inner):self.inner=inner;self.queries=0
        def all(self,*args,**kwargs):self.queries+=1;return self.inner.all(*args,**kwargs)
        def __getattr__(self,name):return getattr(self.inner,name)
    counted=Counter(db);attach_signals(counted,items)
    assert counted.queries<=5
    assert all('signals' in p for p in items)
