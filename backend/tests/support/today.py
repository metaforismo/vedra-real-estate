"""Queue overflow fixtures used only in temporary QA databases."""
from app.db import dump,now
from app.schemas import Listing
from app.services.store import upsert_listing


def today_dataset(db,settings,count=18):
    sid='qa-today'
    db.execute('INSERT INTO sources(id,name,kind,config,created_at) VALUES(?,?,?,?,?)',(sid,'QA · Contatti','import',dump({}),now()))
    ids=[]
    for n in range(count):
        contact={'name':f'QA · Broker {n+1:03d}'}
        if n<12:contact['telephone']='+39020000000'
        if n==12:contact['telephone']='recapito non valido'
        if n==13:contact['email']={'invalid':'not a string'}
        listing=Listing(listing_key=f'today-{n}',title=f'QA · Contatto {n+1:03d}',url=f'https://qa.example/listing/{n}',
                        price=300000+n,surface=100,city='Milano',currency='EUR',transaction_type='sale',availability='listed',
                        evidence={'decision_facts':{'contact':contact}})
        ident=upsert_listing(db,settings,sid,listing)[0];ids.append(ident)
        db.execute("UPDATE properties SET review_status='shortlisted',priority_score=? WHERE id=?",(99-n if n<90 else 1,ident))
    return ids
