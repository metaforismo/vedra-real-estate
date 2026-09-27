from app.db import dump,now,uid
from app.services.benchmark_catalog import catalog


def insert(db,**updates):
    row=dict(id=uid(),city='Milano',zone='Centro',property_type='office',condition='good',area_basis='commercial',currency='USD',transaction_type='sale',min_sqm=1000,max_sqm=2000,period='2025-S2',source_label='QA fonte 100%',source_url='https://example.com/benchmark',is_demo=0,imported_at=now())
    row.update(updates);keys=list(row)
    db.execute('INSERT INTO benchmarks('+','.join(keys)+') VALUES('+','.join('?' for _ in keys)+')',tuple(row[k] for k in keys))
    return row


def test_paginated_benchmarks_keep_currency_provenance_and_literal_search(db):
    for n in range(23):insert(db,id=f'benchmark-{n:04}')
    insert(db,is_demo=1,city='Hidden')
    first=catalog(db);second=catalog(db,page=2)
    assert (first['total'],len(first['items']),len(second['items']))==(23,20,3)
    assert set(r['id'] for r in first['items']).isdisjoint(r['id'] for r in second['items'])
    assert first['currencies']==['USD']
    assert first['items'][0]['source_url']=='https://example.com/benchmark'
    assert catalog(db,q='100%')['total']==23
    assert catalog(db,q='100_')['total']==0
    assert catalog(db,currency='EUR')['total']==0
    assert catalog(db,condition='new')['total']==0
    assert catalog(db,page=999)['page']==2


def test_inventory_reaches_rows_beyond_old_limit(db):
    template=insert(db);keys=list(template)
    sql='INSERT INTO benchmarks('+','.join(keys)+') VALUES('+','.join('?' for _ in keys)+')'
    with db.transaction() as con:
        for n in range(3001):
            row={**template,'id':f'bulk-{n:04}','city':'Zeta target' if n==3000 else 'Milano'}
            con.execute(sql,tuple(row[k] for k in keys))
    result=catalog(db,q='Zeta')
    assert result['archive_total']==3002 and result['total']==1
    assert result['items'][0]['id']=='bulk-3000'


def test_empty_inventory_is_explicit(db):
    result=catalog(db)
    assert result['items']==[] and result['total']==0 and not result['has_next']


def test_inventory_endpoint_validates_and_preserves_auth(api):
    app,client,settings=api
    assert client.get('/api/benchmarks/catalog').status_code==200
    for query in ('page=0','page=abc','currency=TOOLONG','q='+'x'*201):
        assert client.get('/api/benchmarks/catalog?'+query).status_code==422
