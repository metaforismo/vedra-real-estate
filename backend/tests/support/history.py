"""Historical evidence for isolated browser QA only."""
from datetime import datetime, timedelta, timezone
from app.db import dump, uid


def seed_history(db, property_id):
    ids=[]
    for n in range(35):
        ident=uid();ids.append(ident)
        at=(datetime(2025,1,1,tzinfo=timezone.utc)+timedelta(days=n)).isoformat()
        price=100000-n*1000
        fields={'title':'Immobile di collaudo','price':price,'surface':100,'currency':'EUR',
                'transaction_type':'sale','area_basis':'commercial','availability':'listed',
                'description':('Descrizione integrale di collaudo. ' * 35)+f'QA fine del testo storico {n}'}
        db.execute('INSERT INTO observations VALUES(?,?,?,?,?,?,?)',(ident,property_id,at,price,f'qa-history-{n}',None,'qa-history'))
        db.execute('INSERT INTO observation_values VALUES(?,?)',(ident,dump(fields)))
        db.execute('INSERT INTO observation_context(observation_id,currency,transaction_type,area_basis,surface) VALUES(?,?,?,?,?)',(ident,'EUR','sale','commercial',100))
    return ids


def remove_history(db, ids):
    for ident in ids:
        db.execute('DELETE FROM observation_context WHERE observation_id=?',(ident,))
        db.execute('DELETE FROM observation_values WHERE observation_id=?',(ident,))
        db.execute('DELETE FROM observations WHERE id=?',(ident,))
