"""Portal alert emails and results pages. All mails and pages are synthetic fixtures (invented ids, prices
and addresses) under fixtures/portal_alerts; no network, no real portal content."""
import base64
import imaplib
import logging
from dataclasses import replace
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import quote

import pytest
from uuid import uuid4

from app.db import load
from app.services.portal_alerts import check_mailbox, ingest, status
from app.services.portal_cards import CAPITALS, Card, _norm, extract_cards, listing_link, locate, store_cards

FIX = Path(__file__).parent / 'fixtures/portal_alerts'
LISTING = (Path(__file__).parent / 'fixtures/html/listing.html').read_text()
EXT = {'Origin': 'chrome-extension://abcdefghijklmnop'}


def eml(name):
    return (FIX / name).read_bytes()


def mail(sender, body, *, mid, subject='Nuovi annunci', size_pad=0):
    m = EmailMessage()
    m['From'], m['To'], m['Subject'], m['Message-ID'] = sender, 'avvisi@vedra.example', subject, mid
    m['Date'] = 'Mon, 28 Sep 2026 09:00:00 +0200'
    m.set_content('testo')
    m.add_alternative(body + ('<!--' + 'x' * size_pad + '-->' if size_pad else ''), subtype='html')
    return bytes(m)


def card_html(ident, price, extra=''):
    return (f'<table><tr><td><a href="https://www.immobiliare.it/annunci/{ident}/">Trilocale via Crema 12, Porta Romana, Milano</a>'
            f'<p>{price}</p>{extra}</td></tr></table>')


def rows(db, ident):
    return db.all("SELECT * FROM properties WHERE url=?", (f'https://www.immobiliare.it/annunci/{ident}/',))


def observations(db, pid):
    return [r['price'] for r in db.all('SELECT price FROM observations WHERE property_id=? ORDER BY observed_at,id', (pid,))]


# Links -------------------------------------------------------------------------------------------

@pytest.mark.parametrize('href,expected', [
    ('https://www.immobiliare.it/annunci/118765432/?utm_source=alert', 'https://www.immobiliare.it/annunci/118765432/'),
    ('https://immobiliare.it/annunci/118765432', 'https://www.immobiliare.it/annunci/118765432/'),
    ('https://www.immobiliare.it/en/annunci/118765432/', 'https://www.immobiliare.it/annunci/118765432/'),
    ('https://clicks.immobiliare.it/ls/click?upn=a&u=' + quote('https://www.immobiliare.it/annunci/118765432/?x=1', safe=''),
     'https://www.immobiliare.it/annunci/118765432/'),
    ('https://email.idealista.it/c/x?redirect=' + quote(quote('https://www.idealista.it/immobile/31234567/', safe=''), safe=''),
     'https://www.idealista.it/immobile/31234567/'),
    ('https://t.casa.it/r/' + base64.urlsafe_b64encode(b'https://www.casa.it/immobili/47123456/').decode().rstrip('='),
     'https://www.casa.it/immobili/47123456/'),
    ('https://tracker.example/click/' + quote('https://www.casa.it/immobili/47123456/', safe=''), 'https://www.casa.it/immobili/47123456/'),
])
def test_listing_links_are_recovered_from_trackers_without_opening_them(href, expected):
    assert listing_link(href)[0] == expected


@pytest.mark.parametrize('href', [
    'javascript:alert(1)', 'data:text/html;base64,PGgxPng8L2gxPg==', 'mailto:x@immobiliare.it',
    'https://www.immobiliare.it.evil.example/annunci/118765432/', 'https://evilimmobiliare.it/annunci/118765432/',
    'https://user:pw@www.immobiliare.it/annunci/118765432/', 'https://www.immobiliare.it/agenzie-immobiliari/12345/',
    'https://www.immobiliare.it/vendita-case/milano/', 'https://clicks.immobiliare.it/ls/click?upn=opaque123',
    'https://tracker.example/r?u=' + quote('javascript:alert(1)', safe=''), 'https://www.idealista.com/inmueble/31234567/',
])
def test_links_that_are_not_portal_listings_are_rejected(href):
    assert listing_link(href) is None


# Cards -------------------------------------------------------------------------------------------

def test_card_values_come_only_from_the_card_text():
    cards, skipped = extract_cards('''<p>La tua ricerca: fino a 600.000 € <a href="https://x.example/s">Modifica ricerca</a></p>
        <div><a href="https://www.immobiliare.it/annunci/1111111/">Bilocale via Tortona 3, Milano</a>
        <p>€ 350.000 · 1.900 €/m² · rata da 1.200 €/mese</p><p>55 m² · 2 locali</p></div>
        <div><a href="https://www.immobiliare.it/annunci/2222222/">Trilocale in vendita a Milano</a><p>€ 400.000 € 420.000</p><p>90 m² 110 m²</p></div>''')
    one, two = cards
    assert (one.price, one.surface, one.rooms, one.address, one.city) == (350000, 55, 2, 'via Tortona 3, Milano', '')
    # Two prices without a written drop and two surfaces: ambiguous, so none is kept.
    assert (two.price, two.old_price, two.surface, two.city, two.transaction_type) == (None, None, None, 'Milano', 'sale')
    assert skipped == 0


def test_price_drop_takes_the_struck_price_as_the_old_one():
    cards, _ = extract_cards('<div><a href="https://www.casa.it/immobili/47000001/">Loft via Savona 20</a>'
                             '<p><del>520.000 €</del> 480.000 €</p></div>')
    assert (cards[0].price, cards[0].old_price, cards[0].price_drop) == (480000, 520000, True)


def test_three_portal_alerts(db, settings):
    immo = ingest(db, settings, eml('immobiliare_alert.eml'), channel='upload')
    assert (immo['status'], immo['cards'], immo['created'], immo['no_price'], immo['skipped'], immo['price_drops']) == ('processed', 3, 3, 1, 1, 1)
    ideal = ingest(db, settings, eml('idealista_alert.eml'), channel='upload')
    # javascript: and data: links are not listings: those cards are skipped and counted.
    assert (ideal['cards'], ideal['created'], ideal['skipped']) == (2, 2, 2)
    casa = ingest(db, settings, eml('casa_alert.eml'), channel='upload')
    assert (casa['cards'], casa['created']) == (2, 2)
    drop = db.one("SELECT * FROM properties WHERE url='https://www.immobiliare.it/annunci/118700001/'")
    card = load(drop['evidence'])['portal_card']
    assert (drop['price'], drop['surface'], drop['rooms'], drop['source_id']) == (435000, 68, 2, 'capture-www-immobiliare-it')
    assert card['incomplete'] and card['origin'] == 'alert' and card['old_price'] == 460000 and card['price_drop']
    assert card['message_id'] == '<synthetic-immo-0001@notifiche.immobiliare.it>' and card['seen_at'].startswith('2026-09-28T05:12')
    # Photos are references only: nothing is downloaded or served from the card.
    assert load(drop['images']) == [] and card['image_url'] is None
    first = db.one("SELECT * FROM properties WHERE url='https://www.immobiliare.it/annunci/118765432/'")
    assert load(first['evidence'])['portal_card']['image_url'] == 'https://pic.example-cdn.it/synthetic/1.jpg'
    assert load(first['evidence'])['price']['value'] == '€ 520.000'
    casa_row = db.one("SELECT * FROM properties WHERE url='https://www.casa.it/immobili/47123456/'")
    assert (casa_row['city'], casa_row['address'], casa_row['transaction_type'], casa_row['source_id']) == ('Milano', 'Via Savona 45, Tortona', 'sale', 'capture-www-casa-it')
    # A card is not a check of the detail page.
    assert db.one('SELECT COUNT(*) n FROM listing_checks')['n'] == 0
    assert status(db, settings)['totals'] == {'messages': 3, 'read': 3, 'ignored': 0, 'rejected': 0, 'cards': 7, 'created': 7, 'updated': 0, 'skipped': 3}


def test_duplicate_message_id_and_foreign_senders(db, settings):
    assert ingest(db, settings, eml('immobiliare_alert.eml'), channel='upload')['status'] == 'processed'
    before = db.one('SELECT COUNT(*) n FROM observations')['n']
    assert ingest(db, settings, eml('immobiliare_alert.eml'), channel='imap')['status'] == 'duplicate'
    assert db.one('SELECT COUNT(*) n FROM observations')['n'] == before
    body = card_html('3333333', '€ 999.000')
    for sender in ('Offerte <promo@example.com>', 'Falso <noreply@immobiliare.it.evil.example>'):
        assert ingest(db, settings, mail(sender, body, mid=f'<{sender[:5]}@x>'), channel='imap')['status'] == 'ignored'
    assert rows(db, '3333333') == []
    assert status(db, settings)['totals']['ignored'] == 2
    # Forwarded as an attachment by a team member: the portal message inside is read.
    outer = EmailMessage()
    outer['From'], outer['Subject'], outer['Message-ID'] = 'Jacopo <jacopo@studio.example>', 'Fwd', '<fwd-1@studio.example>'
    outer.set_content('Vedi allegato')
    from email import message_from_bytes, policy
    outer.add_attachment(message_from_bytes(mail('Idealista <avvisi@idealista.it>', card_html('3333333', '€ 999.000'), mid='<inner@x>'), policy=policy.default))
    assert ingest(db, settings, bytes(outer), channel='upload')['created'] == 1


def test_oversized_mail_is_rejected_before_parsing(db, settings):
    from app.services.portal_alerts import AlertRejected
    big = mail('Immobiliare.it <noreply@immobiliare.it>', card_html('4444444', '€ 1.000.000'), mid='<big@x>', size_pad=2_100_000)
    with pytest.raises(AlertRejected):
        ingest(db, settings, big, channel='upload')
    assert rows(db, '4444444') == [] and db.one('SELECT COUNT(*) n FROM portal_alert_messages')['n'] == 0


def test_price_cut_from_a_later_alert_is_a_new_observation(db, settings):
    sender = 'Immobiliare.it <noreply@immobiliare.it>'
    ingest(db, settings, mail(sender, card_html('5555555', '€ 460.000', '<p>68 m² · in vendita</p>'), mid='<a1@x>'), channel='imap')
    again = ingest(db, settings, mail(sender, card_html('5555555', '€ 460.000'), mid='<a2@x>'), channel='imap')
    assert again['unchanged'] == 1
    cut = ingest(db, settings, mail(sender, card_html('5555555', 'Prezzo ribassato <s>€ 460.000</s> € 430.000'), mid='<a3@x>'), channel='imap')
    assert cut['updated'] == 1
    row, = rows(db, '5555555')
    # The later card did not repeat the surface: the value stays, never overwritten by a null.
    assert (row['price'], row['surface']) == (430000, 68)
    assert observations(db, row['id']) == [460000, 430000]
    from app.services.signals import attach_signals
    from app.services.store import property_dict
    item = attach_signals(db, [property_dict(row)])[0]
    assert item['signals']['reductions']['count'] == 1 and item['signals']['reductions']['from_price'] == 460000


def test_alert_then_detail_capture_is_one_property(api):
    app, client, _ = api
    db, settings = app.state.db, app.state.settings
    body = card_html('7777777', '€ 650.000', '<p>12 locali · 400 m²</p>')
    ingest(db, settings, mail('Immobiliare.it <noreply@immobiliare.it>', body, mid='<merge@x>'), channel='upload')
    alert_row, = rows(db, '7777777')
    assert load(alert_row['evidence'])['portal_card']['incomplete']
    token = client.post('/api/capture/tokens', json={'label': 'Test'}).json()['token']
    jar = dict(client.cookies); client.cookies.clear()
    try:
        response = client.post('/api/capture', json={'url': 'https://www.immobiliare.it/annunci/7777777/?from=alert', 'html': LISTING},
                               headers={**EXT, 'Authorization': 'Bearer ' + token, 'X-CSRF-Token': ''})
    finally:
        client.cookies.update(jar)
    assert response.status_code == 200, response.text
    assert response.json()['property_id'] == alert_row['id'] and not response.json()['created']
    row, = rows(db, '7777777')
    evidence = load(row['evidence'])
    # Richer data from the detail page, the card's rooms kept, the history of both observations kept.
    assert (row['price'], row['surface'], row['city'], row['rooms']) == (600000, 400, 'Milano', 12)
    assert row['description'].startswith('DATO SINTETICO') and evidence['rooms']['method'].startswith('avviso email')
    assert not evidence['portal_card']['incomplete'] and evidence['portal_card']['completed_at']
    assert observations(db, row['id']) == [650000, 600000]
    assert db.one('SELECT last_detail_at FROM listing_checks WHERE property_id=?', (row['id'],))['last_detail_at']
    # A later alert with the same price does not overwrite the detail data nor add an observation.
    ingest(db, settings, mail('Immobiliare.it <noreply@immobiliare.it>', card_html('7777777', '€ 600.000'), mid='<merge2@x>'), channel='upload')
    after, = rows(db, '7777777')
    assert (after['title'], after['description'], after['surface']) == (row['title'], row['description'], 400)
    assert observations(db, row['id']) == [650000, 600000] and not load(after['evidence'])['portal_card']['incomplete']


def test_upload_and_status_api(api):
    app, client, settings = api
    payload = {'name': 'casa.eml', 'eml_base64': base64.b64encode(eml('casa_alert.eml')).decode()}
    first = client.post('/api/portal-alerts/upload', json=payload)
    assert first.status_code == 200, first.text
    assert first.json()['status'] == 'processed' and first.json()['created'] == 2 and 'property_ids' not in first.json()
    assert client.post('/api/portal-alerts/upload', json=payload).json()['status'] == 'duplicate'
    html = client.post('/api/portal-alerts/upload', json={'html': card_html('8888888', '€ 300.000')})
    assert html.json()['created'] == 1
    assert client.post('/api/portal-alerts/upload', json={'eml_base64': '***'}).status_code == 422
    assert client.post('/api/portal-alerts/upload', json={}).status_code == 422
    big = base64.b64encode(mail('Casa.it <a@casa.it>', 'x', mid='<b@x>', size_pad=2_050_000)).decode()
    assert client.post('/api/portal-alerts/upload', json={'eml_base64': big}).status_code == 413
    state = client.get('/api/portal-alerts').json()
    assert not state['imap']['configured'] and state['recent'][0]['subject'] == 'Testo incollato'
    assert client.post('/api/portal-alerts/check').status_code == 409


# Mailbox -----------------------------------------------------------------------------------------

class FakeImap:
    """Stands in for imaplib.IMAP4_SSL. Only read-only commands exist: any write would fail the test."""

    def __init__(self, messages, *, validity='7', refuse_login=False):
        self.messages, self.validity, self.refuse_login, self.calls = dict(messages), validity, refuse_login, []

    def login(self, user, password):
        self.calls.append(('login', user))
        if self.refuse_login:
            raise imaplib.IMAP4.error(b'[AUTHENTICATIONFAILED] Invalid credentials')

    def select(self, folder, readonly=False):
        self.calls.append(('select', folder, readonly))
        return 'OK', [str(len(self.messages)).encode()]

    def response(self, code):
        return code, [self.validity.encode()]

    def uid(self, command, *args):
        self.calls.append(('uid', command, *args))
        if command == 'SEARCH':
            every = sorted(self.messages)
            found = every if args[1] == 'SINCE' else [u for u in every if u >= int(args[2].split(':')[0])] or every[-1:]
            return 'OK', [' '.join(map(str, found)).encode()]
        assert command == 'FETCH' and args[1] in ('(RFC822.SIZE)', '(BODY.PEEK[])'), args
        raw = self.messages[int(args[0])]
        if args[1] == '(RFC822.SIZE)':
            return 'OK', [f'1 (UID {args[0]} RFC822.SIZE {len(raw)})'.encode()]
        return 'OK', [(f'1 (UID {args[0]} BODY[] {{{len(raw)}}}'.encode(), raw), b')']

    def logout(self):
        self.calls.append(('logout',))

    def __getattr__(self, name):
        raise AssertionError(f'IMAP command not allowed: {name}')


@pytest.fixture
def mailbox_settings(settings):
    return replace(settings, alerts_imap_host='imap.example', alerts_imap_user='avvisi@vedra.example',
                   alerts_imap_password='test-only-imap-secret')


def test_mailbox_is_read_only_and_resumes_after_the_last_message(db, mailbox_settings, caplog):
    box = FakeImap({11: eml('immobiliare_alert.eml'), 12: mail('Promo <x@example.com>', card_html('9999999', '€ 1.000'), mid='<p@x>'),
                    13: mail('Casa.it <a@casa.it>', card_html('9999998', '€ 1.000.000'), mid='<big@x>', size_pad=2_100_000)})
    caplog.set_level(logging.DEBUG)
    result = check_mailbox(db, mailbox_settings, connect=lambda s: box)
    assert (result['read'], result['ignored'], result['rejected'], result['created'], result['error']) == (1, 1, 1, 3, None)
    assert ('select', '"INBOX"', True) in box.calls and box.calls[-1] == ('logout',)
    assert not any(c[0] == 'uid' and c[1] == 'FETCH' and 'BODY[]' in c[3] and 'PEEK' not in c[3] for c in box.calls)
    # The oversized message was never downloaded.
    assert ('uid', 'FETCH', '13', '(BODY.PEEK[])') not in box.calls
    state = db.one("SELECT * FROM portal_alert_state WHERE id='imap'")
    assert (state['last_uid'], state['uid_validity'], state['ok']) == (13, '7', 1)
    box.messages[14] = eml('casa_alert.eml')
    box.calls.clear()
    second = check_mailbox(db, mailbox_settings, connect=lambda s: box)
    assert (second['read'], second['created']) == (1, 2)
    assert [c[2] for c in box.calls if c[:2] == ('uid', 'FETCH') and c[3] == '(BODY.PEEK[])'] == ['14']
    box.calls.clear()
    assert check_mailbox(db, mailbox_settings, connect=lambda s: box)['read'] == 0
    assert 'test-only-imap-secret' not in caplog.text


def test_mailbox_errors_are_plain_and_never_show_the_password(db, mailbox_settings, caplog):
    caplog.set_level(logging.DEBUG)
    refused = check_mailbox(db, mailbox_settings, connect=lambda s: FakeImap({}, refuse_login=True))
    assert refused['error'] == 'Accesso alla casella rifiutato: controlla utente e password nel file .env.'

    def unreachable(settings):
        raise OSError('connection refused')
    down = check_mailbox(db, mailbox_settings, connect=unreachable)
    assert down['error'] == 'Casella imap.example non raggiungibile.'
    shown = status(db, mailbox_settings)
    assert shown['error'] == down['error'] and shown['imap'] == {'configured': True, 'host': 'imap.example',
        'user': 'avvisi@vedra.example', 'folder': 'INBOX', 'poll_minutes': 15}
    assert 'test-only-imap-secret' not in repr(shown) + caplog.text + repr(mailbox_settings)


# Results page through Vedra Capture --------------------------------------------------------------

def test_results_page_capture_imports_every_visible_card(api):
    app, client, _ = api
    token = client.post('/api/capture/tokens', json={'label': 'Test'}).json()['token']
    headers = {**EXT, 'Authorization': 'Bearer ' + token, 'X-CSRF-Token': ''}
    page = (FIX / 'immobiliare_results.html').read_text()
    jar = dict(client.cookies); client.cookies.clear()
    try:
        first = client.post('/api/capture', json={'url': 'https://www.immobiliare.it/vendita-case/milano/tortona/', 'html': page}, headers=headers)
        again = client.post('/api/capture', json={'url': 'https://www.immobiliare.it/vendita-case/milano/tortona/', 'html': page}, headers=headers)
        ideal = client.post('/api/capture', json={'url': 'https://www.idealista.it/vendita-case/milano-milano/',
                                                   'html': (FIX / 'idealista_results.html').read_text()}, headers=headers)
    finally:
        client.cookies.update(jar)
    body = first.json()
    assert first.status_code == 200 and body['kind'] == 'results'
    assert (body['cards'], body['created'], body['updated'], body['no_price'], body['portal']) == (3, 3, 0, 1, 'immobiliare.it')
    assert (again.json()['created'], again.json()['unchanged']) == (0, 3)
    assert (ideal.json()['cards'], ideal.json()['price_drops']) == (2, 1)
    db = app.state.db
    row = db.one("SELECT * FROM properties WHERE url='https://www.idealista.it/immobile/31300002/'")
    assert row['source_id'] == 'capture-www-idealista-it' and load(row['evidence'])['portal_card']['origin'] == 'results_page'
    assert row['transaction_type'] == 'sale' and 'vendita-case' in load(row['evidence'])['transaction_type']['value']


def test_protected_portals_are_never_fetched_by_the_server(settings):
    from app.connectors.safe_http import SafeFetcher, SourceBlocked
    allowed = replace(settings, live_domains=['www.immobiliare.it'])
    with pytest.raises(SourceBlocked, match='Vedra Capture'):
        SafeFetcher('www.immobiliare.it', allowed).validate_url('https://www.immobiliare.it/annunci/1/')


def test_worker_checks_the_mailbox_once_per_interval(db, mailbox_settings, monkeypatch):
    import asyncio
    from app.services import portal_alerts
    from app.services.engine import Engine
    calls = []
    monkeypatch.setattr(portal_alerts, 'check_mailbox', lambda db, settings: calls.append(settings.alerts_imap_host) or {})
    engine = Engine(db, mailbox_settings)

    async def ticks():
        engine.poll_alerts()
        await engine.alerts_task
        engine.poll_alerts()  # next tick: not due for another ALERTS_POLL_MINUTES
    asyncio.run(ticks())
    assert calls == ['imap.example']


# Location --------------------------------------------------------------------------------------

KNOWN = {_norm(n): n for n in [*CAPITALS, 'Sesto San Giovanni']}


def located(address, *, text='', context=''):
    card = Card(url='u', portal='immobiliare.it', listing_id='1', title='t', text=text or address or '', address=address)
    locate(card, KNOWN, context)
    return card.address, card.zone, card.city


@pytest.mark.parametrize('address,expected', [
    ('via Crema 12, Porta Romana, Milano', ('via Crema 12', 'Porta Romana', 'Milano')),
    ('via Tortona, 31, Tortona, Milano', ('via Tortona, 31', 'Tortona', 'Milano')),
    ('viale Umbria 7, Milano', ('viale Umbria 7', '', 'Milano')),
    ('corso Lodi 40, Lodi, Milano', ('corso Lodi 40', 'Lodi', 'Milano')),
    ('via Roma 3, Sesto San Giovanni', ('via Roma 3', '', 'Sesto San Giovanni')),
    # The last element is not a known comune: nothing is inferred.
    ('Via Savona 45, Tortona', ('Via Savona 45, Tortona', '', '')),
    ('via Crema 12', ('via Crema 12', '', '')),
])
def test_comune_from_the_card_location_line(address, expected):
    assert located(address) == expected


def test_comune_from_the_alert_subject_only_without_conflicts():
    subject = '3 nuovi annunci per «Milano Porta Romana»'
    assert located(None, text='Bilocale luminoso € 300.000', context=subject)[2] == 'Milano'
    # A street named after another city is not another place; the place itself is.
    assert located(None, text='Bilocale via Padova 10 € 300.000', context=subject)[2] == 'Milano'
    assert located(None, text='Bilocale a Monza € 300.000', context=subject)[2] == ''
    assert located(None, text='Casa con prato', context='Nuovi annunci: villa con prato')[2] == ''
    assert located(None, text='Bilocale', context='Nuovi annunci: Milano e Monza')[2] == ''


def test_alert_cards_get_comune_zone_and_searches(api):
    app, client, settings = api
    db = app.state.db
    agent = client.post('/api/agents', json={'name': 'Milano sotto 700k', 'city': 'Milano', 'source_ids': ['demo-milano'],
                                             'criteria': {'max_price': 700000}, 'interval_minutes': 0, 'request_id': str(uuid4())})
    assert agent.status_code in (200, 201), agent.text
    ingest(db, settings, eml('immobiliare_alert.eml'), channel='upload')
    row = db.one("SELECT * FROM properties WHERE url='https://www.immobiliare.it/annunci/118765432/'")
    evidence = load(row['evidence'])
    assert (row['city'], row['zone'], row['address'], row['property_type']) == ('Milano', 'Porta Romana', 'via Crema 12', 'residential')
    assert load(row['evidence'])['property_type']['value'] == 'Trilocale'
    assert evidence['city']['value'] == 'via Crema 12, Porta Romana, Milano' and 'comune noto' in evidence['city']['method']
    assert db.one('SELECT COUNT(*) n FROM agent_properties WHERE property_id=? AND agent_id=?', (row['id'], agent.json()['id']))['n'] == 1
    # A card is not an availability check: never closed, still found by the default "Non archiviati" view.
    assert row['availability'] == 'unknown'
    from app.catalog_schemas import CatalogQuery
    from app.services.catalog import search
    assert row['id'] in [p['id'] for p in search(db, CatalogQuery(q='Crema'))['items']]
