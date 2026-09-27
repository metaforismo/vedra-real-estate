from app.db import now
from app.schemas import Listing
from app.services.brokers import directory
from app.services.store import upsert_listing


def put(db, settings, key, price, contact, city='Milano', zone='Brera', description='', availability='listed', currency='EUR'):
    if not db.one("SELECT id FROM sources WHERE id='qa-brokers'"):
        db.execute('INSERT INTO sources(id,name,kind,config,created_at) VALUES(?,?,?,?,?)', ('qa-brokers', 'QA · Broker', 'import', '{}', now()))
    listing = Listing(listing_key=key, url=f'https://qa.example/{key}', title=f'QA · {key}', description=description, price=price,
                      surface=200, city=city, zone=zone, currency=currency, transaction_type='sale', availability=availability,
                      evidence={'decision_facts': {'contact': contact}} if contact else {})
    return upsert_listing(db, settings, 'qa-brokers', listing)[0]


def test_phone_formats_and_email_group_one_advertiser(db, settings):
    put(db, settings, 'a', 4_500_000, {'name': 'Studio Brera', 'telephone': '+39 02 1234 5678'})
    put(db, settings, 'b', 5_200_000, {'name': 'Studio Brera srl', 'telephone': '0212345678', 'email': 'Info@Brera.example'})
    put(db, settings, 'c', 900_000, {'name': 'Altro', 'email': 'info@brera.example'})
    result = directory(db)
    assert result['total'] == 1
    broker = result['items'][0]
    assert broker['count'] == 3 and broker['value_eur'] == 10_600_000 and broker['max_price_eur'] == 5_200_000
    assert broker['email'] == 'info@brera.example' and broker['listings'][0]['price'] == 5_200_000


def test_high_value_city_filter_matches_the_client_example(db, settings):
    put(db, settings, 'centro', 4_200_000, {'name': 'Broker Centro', 'telephone': '+390211111111'}, zone='Duomo')
    put(db, settings, 'small', 350_000, {'name': 'Broker Piccolo', 'telephone': '+390222222222'})
    put(db, settings, 'rome', 6_000_000, {'name': 'Broker Roma', 'telephone': '+390633333333'}, city='Roma')
    put(db, settings, 'usd', 9_000_000, {'name': 'Broker USD', 'telephone': '+390244444444'}, currency='USD')
    names = [b['name'] for b in directory(db, city='milano', min_price=4_000_000)['items']]
    assert names == ['Broker Centro']


def test_direct_declarations_rank_first_and_can_be_required(db, settings):
    put(db, settings, 'agency', 800_000, {'name': 'Agenzia', 'telephone': '+390255555555'})
    put(db, settings, 'owner', 700_000, {'name': 'Privato', 'telephone': '+393351234567'}, description='Vendita diretta dal proprietario.')
    items = directory(db)['items']
    assert items[0]['name'] == 'Privato' and items[0]['direct'] == 1
    assert [b['name'] for b in directory(db, direct_only=True)['items']] == ['Privato']


def test_unattributed_closed_and_search(db, settings):
    put(db, settings, 'none', 500_000, None)
    put(db, settings, 'sold', 500_000, {'name': 'Venduto', 'telephone': '+390266666666'}, availability='sold')
    put(db, settings, 'named', 500_000, {'organization': 'Gruppo Navigli'}, zone='Navigli')
    result = directory(db)
    assert result['unattributed'] == 1 and result['total'] == 1 and result['examined'] == 2
    assert directory(db, q='navigli')['total'] == 1 and directory(db, q='zzz')['total'] == 0


def test_api_returns_directory_and_validates_input(api):
    _, client, _ = api
    body = client.get('/api/brokers?min_price=1000000&direct_only=true').json()
    assert set(body) >= {'items', 'total', 'unattributed', 'examined', 'limited'}
    assert client.get('/api/brokers?min_price=-1').status_code == 422


def test_insights_count_reductions_and_below_benchmark(db, settings):
    from app.services.insights import workspace_insights
    ident = put(db, settings, 'cut', 500_000, None)
    put(db, settings, 'cut', 450_000, None)
    db.execute('UPDATE properties SET discount=15 WHERE id=?', (ident,))
    archive = workspace_insights(db)['archive']
    assert archive['reduced'] == 1 and archive['below_benchmark'] == 1
