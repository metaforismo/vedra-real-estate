from app.db import now
from app.services.today import queue
from support.today import today_dataset


def test_complete_bounded_queue_and_invalid_contacts(db,settings):
    ids=today_dataset(db,settings)
    result=queue(db)
    assert len(result['call'])==12 and len(result['verify'])==6
    assert result['examined']==18 and not result['limited']
    assert {r['id'] for r in result['call']+result['verify']}==set(ids)
    assert all('Recapito da trovare' in r['checks'] for r in result['verify'])
    assert all(r['contact'].get('telephone')=='+39020000000' for r in result['call'])


def test_queue_limit_is_explicit_and_closed_assets_stay_out(db,settings):
    ids=today_dataset(db,settings,103)
    result=queue(db)
    assert result['limited'] and result['examined']==100
    assert len(result['call'])+len(result['verify'])==100
    db.execute("UPDATE properties SET availability='sold' WHERE id=?",(ids[0],))
    assert ids[0] not in {r['id'] for group in ('call','verify') for r in queue(db)[group]}


def test_representative_deduplication_survives_expanded_queue(db,settings):
    ids=today_dataset(db,settings)
    db.execute('INSERT INTO users VALUES(?,?,?,?,?,?)',('qa-user','qa@example.test','unused','QA','analyst',now()))
    a,b=sorted(ids[:2]);db.execute('INSERT INTO duplicate_reviews VALUES(?,?,?,?,?)',(a,b,'same_asset','qa-user',now()))
    result=queue(db)
    assert len(result['call'])==11
    assert len({r['id'] for r in result['call']} & {a,b})==1
