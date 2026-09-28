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


def test_portal_cards_to_open_have_their_own_group_newest_first(db,settings):
    from app.services.portal_cards import Card, store_cards
    from app.services.catalog import search
    from app.catalog_schemas import CatalogQuery
    query=lambda **f:search(db,CatalogQuery(**f))
    ids=today_dataset(db,settings)
    assert queue(db)['portals']=={'items':[],'total':0}
    card=lambda n,**extra:Card(url=f'https://www.immobiliare.it/annunci/{n}/',portal='immobiliare.it',listing_id=str(n),
                               title=f'Trilocale {n}',text='t',city='Milano',zone='Centro',currency='EUR',**extra)
    first=store_cards(db,settings,[card(1,price=500000)],origin='alert',seen_at='2026-09-27T09:00:00Z')['property_ids'][0]
    db.execute("UPDATE properties SET first_seen='2026-09-27T09:00:00+00:00' WHERE id=?",(first,))
    cut=store_cards(db,settings,[card(2,price=460000,old_price=500000,price_drop=True)],origin='results_page')['property_ids'][0]
    # Shortlisted by the team, still without a contact: it moves from "Da verificare" to the portal group.
    db.execute("UPDATE properties SET review_status='shortlisted' WHERE id=?",(first,))
    result=queue(db)
    portals=result['portals']
    assert portals['total']==2 and [r['id'] for r in portals['items']]==[cut,first]
    assert portals['items'][0]['drop_pct']==-8.0 and portals['items'][1]['drop_pct'] is None
    assert portals['items'][0]['url']=='https://www.immobiliare.it/annunci/2/' and portals['items'][0]['portal']=='immobiliare.it'
    assert first not in {r['id'] for r in result['verify']} and set(ids)>={r['id'] for r in result['call']+result['verify']}
    # The archive focus lists exactly the same rows; a completed or discarded card leaves both.
    assert {r['id'] for r in query(focus='portal')['items']}=={first,cut}
    db.execute("UPDATE properties SET review_status='discarded' WHERE id=?",(cut,))
    assert queue(db)['portals']['total']==1 and query(focus='portal')['total']==1
