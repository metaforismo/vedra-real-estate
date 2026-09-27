"""Data-quality cases for the isolated UI test database."""
from app.db import now,uid
from app.schemas import Listing
from app.services.store import upsert_listing


def seed_quality(db,settings):
    sources=[]
    for name in ('QA · Fonte uno','QA · Fonte due'):
        sid=uid();sources.append(sid)
        db.execute("INSERT INTO sources(id,name,kind,created_at) VALUES(?,?,'import',?)",(sid,name,now()))
    ids=[]
    for n in range(3):
        listing=Listing(listing_key=f'quality-{n}',url=f'import://quality/{n}',
            title='QA · Ufficio centrale' if n==0 else 'QA · Ufficio con doppio ingresso e spazi da riorganizzare' if n==1 else 'QA · Annuncio archiviato senza prezzo',
            city='Torino',zone='Centro',address='Via controllo 12' if n<2 else 'Via controllo 24',
            property_type='office',condition='good',price=100000+n*10000 if n<2 else None,surface=100,
            currency='EUR',transaction_type='sale',area_basis='commercial',availability='listed' if n<2 else 'sold',
            description='Record sintetico per collaudo locale della qualità.')
        ids.append(upsert_listing(db,settings,sources[n%2],listing)[0])
    return ids
