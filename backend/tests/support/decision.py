"""Rich decision-screen fixtures. Never imported by application code."""
from datetime import datetime
from app.db import now,dump
from app.schemas import Listing
from app.services.store import upsert_listing


def decision_dataset(db,settings,user_id):
    for n in range(3):
        sid=f'qa-evidence-{n}'
        db.execute('INSERT INTO sources(id,name,kind,domain,config,created_at) VALUES(?,?,?,?,?,?)',
                   (sid,f'QA · Fonte {n+1}','import',f'qa{n}.example',dump({}),now()))
    common={'city':'Milano','zone':'QA · Zona confronto','surface':100,'currency':'EUR','transaction_type':'sale','area_basis':'commercial','property_type':'residential','availability':'listed'}
    def put(key,price,condition,source=0,evidence=None):
        listing=Listing(listing_key=key,url=f'https://qa{source}.example/listing/{key}',title=f'QA · {key}',price=price,condition=condition,evidence=evidence or {},**common)
        return upsert_listing(db,settings,f'qa-evidence-{source}',listing)[0]
    contact={'name':'QA · Broker diretto','telephone':'+39020000000','email':'qa@example.test','role':'Inserzionista dichiarato'}
    omi={'status':'available','period':f'{datetime.now().year}-S1','zone_code':'QA','zone_label':'Zona test','source_label':'OMI · dati QA','source_url':'https://qa0.example/omi', 'retrieved_at':now(),'rows':[{'type':'Abitazioni civili','condition':'NORMALE','min_sqm':2800,'max_sqm':4000,'area_basis':'gross'}]}
    subject=put('Asset da approfondire',290000,'to_renovate',evidence={'decision_facts':{'contact':contact},'market_context':omi})
    linked=put('Stesso asset, altra fonte',310000,'to_renovate',1,{'decision_facts':{'contact':contact|{'name':'QA · Secondo broker','telephone':'+39020000001'}}})
    a,b=sorted((subject,linked))
    db.execute('INSERT INTO duplicate_reviews VALUES(?,?,?,?,?)',(a,b,'same_asset',user_id,now()))
    db.execute("UPDATE properties SET review_status='shortlisted' WHERE id IN (?,?)",(subject,linked))
    comparables=[]
    for condition,prices in [('to_renovate',(320000,340000,360000)),('renovated',(450000,480000,510000)),('new',(540000,570000,610000))]:
        for n,price in enumerate(prices):comparables.append(put(f'{condition} {n+1}',price,condition,n))
    return subject,linked,comparables
