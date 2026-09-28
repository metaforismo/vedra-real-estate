"""Regressions from the live accuracy study of 28 September 2026 (25 listings on 7 agency sites).

Pages are synthetic replicas of the layouts that misled Scout (fixtures/html/scout, invented data); each model answer
reproduces what qwen3.8-27b actually returned on the real page. The deterministic checks must keep what the page
states and drop what it does not."""
from pathlib import Path

from app.connectors.parser import extract_listing
from app.db import dump, load, now
from app.schemas import Criteria
from app.services.decision_facts import text_facts
from app.services.engine import Engine
from app.connectors.safe_http import SafeFetcher
from app.services.scout import ScoutModel, digest_page, extract, open_points, plan_page

from test_scout import model_transport, scout_settings

PAGES = Path(__file__).parent / 'fixtures' / 'html' / 'scout'
BASE = {'title': 'Annuncio', 'currency': 'EUR', 'city': 'Milano', 'property_type': 'residential', 'transaction': 'sale', 'quotes': {}}


async def read(settings, page, answer, url='https://agency.example/annuncio/1'):
    transport, _ = model_transport({'extract': {**BASE, **answer}})
    return await extract(ScoutModel(scout_settings(settings), transport), (PAGES / page).read_text(), url)


async def test_condition_label_values_and_split_phones_are_kept(settings):
    # "Condizioni dell’immobile Buono" was dropped (vocabulary), two numbers in one field lost the phone and a
    # one-letter slip in the e-mail lost the address.
    listing = await read(settings, 'franchise_details.html', {
        'price': 398000, 'surface_sqm': 80, 'condition': 'good', 'quotes': {'condition': 'Buono'},
        'advertiser': {'name': 'Agenzia Rete Test Milano Centro Esempio Snc', 'telephone': '0200000001 3330000001',
                       'email': 'milanocntro@retetest.example', 'kind': 'agency'}})
    assert listing.condition == 'good'
    contact = listing.evidence['decision_facts']['contact']
    assert contact['telephone'] == '0200000001' and contact['email'] == 'milanocentro@retetest.example'


async def test_bare_adjective_needs_a_condition_label(settings):
    listing = await read(settings, 'franchise_details.html', {'price': 398000, 'condition': 'good', 'quotes': {'condition': 'signorile'}})
    assert listing.condition == 'unknown'
    from app.services.scout import _condition_supported
    assert not _condition_supported('good', 'Buono', 'Un buono sconto per il trasloco')
    assert _condition_supported('good', 'Buono', 'Condizioni dell’immobile Buono Riscaldamento')
    assert not _condition_supported('good', 'Condizioni immobile Discrete')
    assert not _condition_supported('good', 'finiture di livello')
    assert not _condition_supported('renovated', 'Lo stabile è di recente ristrutturato')
    assert _condition_supported('renovated', 'appartamento ristrutturato in stabile d’epoca')
    assert not _condition_supported('new', 'tetto nuovo') and _condition_supported('new', 'Nuove costruzioni')


async def test_cadastral_code_without_slash_and_basis_tied_to_the_figure(settings):
    listing = await read(settings, 'online_agency.html', {
        'price': 460000, 'surface_sqm': 65, 'surface_basis': 'commercial', 'cadastral_category': 'A3', 'condition': 'renovated',
        'quotes': {'condition': 'completamente ristrutturato'},
        'advertiser': {'name': 'Giulia Esempio', 'organization': 'Agenzia Online Test', 'telephone': '02 00000099', 'email': 'info@agenziaonline.example', 'kind': 'agent'}})
    facts = listing.evidence['decision_facts']
    assert facts['cadastral']['quote'] == 'Categoria catastale A/3'
    assert listing.area_basis == 'commercial'
    # The address sits only in a mailto link: it is shown where it is published and kept.
    assert facts['contact']['email'] == 'info@agenziaonline.example' and facts['contact']['role'] == 'Agente indicato nell’annuncio'
    other = await read(settings, 'online_agency.html', {'price': 460000, 'surface_sqm': 65, 'cadastral_category': 'A/2'})
    assert 'cadastral' not in other.evidence.get('decision_facts', {})


async def test_basis_of_another_figure_and_legal_dates_are_rejected(settings):
    # Headline 100 m², "103 mq commerciali" in the description: 100 is not commercial. The 2009 date is a bank notice.
    listing = await read(settings, 'network_agent.html', {
        'price': 1100000, 'surface_sqm': 100, 'surface_basis': 'commercial', 'published_date': '2009-07-29',
        'description_start': "La residenza, di 103 mq commerciali, occupa", 'description_end': "l'immobile è trasformabile in abitazione.",
        'advertiser': {'name': 'Paola Esempio', 'organization': 'Rete Esempio Valori - Milano', 'telephone': '329 ...', 'kind': 'agent'}})
    assert listing.surface == 100 and listing.area_basis == 'unknown'
    facts = listing.evidence['decision_facts']
    assert 'published_at' not in facts and 'telephone' not in facts['contact']
    declared = text_facts(listing.title, listing.description)
    assert declared['cadastral']['quote'] == 'Accatastato ad uso ufficio' and 'trasformabile in abitazione' in declared['change_of_use']['quote']


async def test_staff_names_are_not_the_listing_agent_and_price_update_is_the_listings_own(settings):
    listing = await read(settings, 'franchise_staff.html', {
        'price': 420000, 'surface_sqm': 108,
        'advertiser': {'name': 'Marco Esempio', 'organization': 'Progetto Esempio Srl', 'telephone': '0200000002', 'email': 'esempio0@retecase.example', 'kind': 'agent'}})
    facts = listing.evidence['decision_facts']
    assert 'name' not in facts['contact'] and facts['contact']['organization'] == 'Progetto Esempio Srl'
    assert facts['contact']['role'] == 'Agenzia inserzionista'
    assert facts['price_update'] == {'quote': 'Prezzo aggiornato', 'status': 'dichiarato nella fonte'}
    # The same page with the listing's price not flagged: the other card's label is not borrowed.
    page = (PAGES / 'franchise_staff.html').read_text().replace('€ 420.000 Prezzo aggiornato', '€ 420.000')
    transport, _ = model_transport({'extract': {**BASE, 'price': 420000}})
    plain = await extract(ScoutModel(scout_settings(settings), transport), page, 'https://agency.example/annuncio/1')
    assert 'price_update' not in plain.evidence.get('decision_facts', {})


async def test_network_head_office_number_is_not_the_contact(settings):
    hq = await read(settings, 'affiliate_hq_footer.html', {
        'price': 279000, 'condition': 'good', 'quotes': {'condition': 'Condizioni immobile Discrete'},
        'advertiser': {'name': 'Carlo Esempio', 'organization': 'Agenzia Ripamonti Test', 'telephone': '+39 06 000000', 'kind': 'agent'}})
    contact = hq.evidence['decision_facts']['contact']
    assert 'telephone' not in contact and 'name' not in contact and hq.condition == 'unknown'
    # The "Chiama" button of the listing publishes the agency number only in its link: now visible and accepted.
    own = await read(settings, 'affiliate_hq_footer.html', {'price': 279000, 'advertiser': {'organization': 'Agenzia Ripamonti Test', 'telephone': '02/00000003'}})
    assert own.evidence['decision_facts']['contact']['telephone'] == '0200000003'


async def test_publication_dates_from_json_ld_of_this_page(settings):
    listing = await read(settings, 'jsonld_posted.html', {'price': 2400000, 'surface_sqm': 428, 'change_of_use_quote':
                         'Può essere trasformato in un progetto residenziale con più appartamenti di piccola metratura.'},
                         url='https://agency.example/exposes/1')
    facts = listing.evidence['decision_facts']
    assert facts['published_at'].startswith('2026-09-25') and 'trasformato in un progetto residenziale' in facts['change_of_use']['quote']
    wp = await read(settings, 'wordpress_article.html', {'price': 580000, 'surface_sqm': 120, 'condition': 'good', 'quotes': {'condition': 'STATO buono'}},
                    url='https://agency.example/ampio-trilocale/')
    # The article that is this page, not another page's date and not dateModified.
    assert wp.evidence['decision_facts']['published_at'].startswith('2026-09-12') and wp.condition == 'good'


def test_parser_reads_date_posted_on_listing_wrappers():
    html = (PAGES / 'jsonld_posted.html').read_text()
    listing = extract_listing(html, 'https://agency.example/exposes/1')
    assert listing.price == 2400000 and listing.evidence['decision_facts']['published_at'].startswith('2026-09-25')


def test_declared_facts_patterns():
    assert text_facts('', 'Categoria catastale A3 Riscaldamento')['cadastral']['quote'] == 'Categoria catastale A/3'
    assert text_facts('', 'Stabile ristrutturato. Classe energetica A4.') == {}
    assert text_facts('', "L'attico è stato trasformato in due appartamenti.") == {}
    assert text_facts('', 'nato come trilocale, convertito in ampio bilocale') == {}
    assert 'conversione in uffici' in text_facts('', 'Ottima possibilità di conversione in uffici.')['change_of_use']['quote']


RESULTS = '''<html><head><title>Case in vendita a Milano</title></head><body>
<ul><li><a href="/ricerca/Agrigento">Agrigento</a> Agrigento Alessandria Ancona</li><li><a href="/ricerca/Alessandria">Alessandria</a> Agrigento Alessandria Ancona</li>
<li><a href="/ricerca/Ancona">Ancona</a> Agrigento Alessandria Ancona</li></ul>
<div class="grid"><div class="card"><div class="photo"><a href="/comune-milano/1-ufficio-via-esempio"></a><span>Nuovo 1 / 5</span></div>
<p>Ufficio in vendita, Via Esempio, Milano € 1.400.000 420 m² accatastato ufficio, convertibile in residenziale</p></div>
<div class="card"><a href="/comune-milano/2-bilocale">Previous slide Next slide 1 / 47 Bilocale in Via Altra, Milano 320.000 € 60 m²</a></div>
<div class="filler">''' + 'Testo lungo della pagina. ' * 30 + '''</div></div></body></html>'''


async def test_results_cards_keep_their_text_and_reasons_are_card_quotes(settings):
    page = digest_page(RESULTS, 'https://agency.example/cerca')
    links = {l['url'].rsplit('/', 1)[1]: l for l in page['links']}
    # An empty image link still carries its card; carousel counters are gone.
    assert '1.400.000' in links['1-ufficio-via-esempio']['context'] and 'Nuovo' in links['1-ufficio-via-esempio']['context']
    assert links['2-bilocale']['text'].startswith('Bilocale in Via Altra') and 'slide' not in links['2-bilocale']['text']
    office = links['1-ufficio-via-esempio']['id']
    transport, calls = model_transport({'nav': {'listing_ids': [office], 'why': {str(office): 'accatastato ufficio, convertibile in residenziale'},
                                                'other_listing_ids': [links['2-bilocale']['id']], 'follow_ids': [], 'next_id': None, 'note': ''}})
    agent = {'city': 'Milano', 'criteria': {'research_instructions': 'Uffici da convertire in residenziale sopra 1 M'}}
    plan = await plan_page(ScoutModel(scout_settings(settings), transport), page, agent)
    assert plan['reasons'] == {'https://agency.example/comune-milano/1-ufficio-via-esempio': 'accatastato ufficio, convertibile in residenziale'}
    # A menu block repeated around many links is sent once per link no more.
    import json
    sent = json.loads(calls[0]['messages'][1]['content'])['links']
    assert not any('context' in l for l in sent if l.get('text') in ('Agrigento', 'Alessandria', 'Ancona'))
    # An invented reason is not shown as if it came from the card.
    transport, _ = model_transport({'nav': {'listing_ids': [office], 'why': {str(office): 'rendimento 7% garantito'}, 'next_id': None}})
    plan = await plan_page(ScoutModel(scout_settings(settings), transport), page, agent)
    assert plan['listings'] and plan['reasons'] == {}


async def test_run_records_why_each_listing_was_kept_and_what_is_missing(db, settings, monkeypatch):
    s = scout_settings(settings)
    db.execute('INSERT INTO sources(id,name,kind,domain,config,permission_at,permission_note,created_at) VALUES(?,?,?,?,?,?,?,?)',
               ('agency', 'Agenzia test', 'html', 'agency.example', dump({'search_url': 'https://agency.example/cerca', 'max_pages': 1}),
                now(), 'QA fixture only.', now()))
    criteria = Criteria(max_listings=5, max_price=5_000_000, research_instructions='Uffici da convertire in residenziale').model_dump()
    db.execute('INSERT INTO agents VALUES(?,?,?,?,?,?,0,1,NULL,?,?)', ('scout-agent', 'Scout QA', 'Milano', dump(criteria), dump(['agency']), 'scout', now(), now()))
    listing_page = (PAGES / 'jsonld_posted.html').read_text()

    async def fetch(self, url):
        return (RESULTS if 'cerca' in url else listing_page), url
    monkeypatch.setattr(SafeFetcher, 'get', fetch)
    office = next(l['id'] for l in digest_page(RESULTS, 'https://agency.example/cerca')['links'] if 'ufficio' in l['url'])
    transport, _ = model_transport({'nav': {'listing_ids': [office], 'why': {str(office): 'accatastato ufficio'}, 'next_id': None, 'note': 'Un ufficio.'},
                                    'extract': {**BASE, 'title': 'Ampio immobile in via Esempio', 'price': 2400000, 'surface_sqm': 428,
                                                'description_start': 'L’immobile, attualmente accatastato come ufficio', 'description_end': 'più appartamenti di piccola metratura.'}})
    import app.services.scout as scout_module
    original = scout_module.ScoutModel.__init__
    monkeypatch.setattr(scout_module.ScoutModel, '__init__', lambda self, st, t=None: original(self, st, transport))
    from app.services.llm import ChatModelClient

    async def classify(self, payload):
        return {'summary': 'ok', 'strategies': [], 'caveats': [], 'engine': 'llm', 'model': 'q'}, {'input_tokens': 1, 'output_tokens': 1, 'estimated_eur': None, 'usage_reported': True}
    monkeypatch.setattr(ChatModelClient, 'classify', classify)
    engine = Engine(db, s)
    run = engine.enqueue('scout-agent'); await engine.execute(run['id'])
    event = db.one("SELECT data FROM events WHERE run_id=? AND step='extract' AND message LIKE 'Acquisito%'", (run['id'],))
    data = load(event['data'])
    assert data['fit'] is True and data['reason'] == 'accatastato ufficio'
    # Price and surface are stated; condition, basis and a phone are not. The change of use is declared in the text.
    assert data['open'] == ['base della superficie', 'stato', 'recapito']


def test_open_points_follow_the_brief():
    from app.schemas import Listing
    listing = Listing(listing_key='k', url='https://agency.example/1', title='Negozio', price=100000, surface=50, area_basis='commercial',
                      condition='good', evidence={'decision_facts': {'contact': {'telephone': '0200000000'}}})
    assert open_points(listing, {'criteria': {'research_instructions': 'negozi'}}) == []
    assert open_points(listing, {'criteria': {'research_instructions': "negozi con cambio d'uso e categoria catastale"}}) == ['catasto', 'cambio d’uso']


async def test_typographic_apostrophes_and_call_buttons(settings):
    # The model quoted "dell'immobile" for the page's "dell’immobile": same words, kept.
    listing = await read(settings, 'franchise_details.html', {'price': 398000, 'condition': 'good', 'quotes': {'condition': "Condizioni dell'immobile Buono"}})
    assert listing.condition == 'good'
    page = digest_page((PAGES / 'affiliate_hq_footer.html').read_text().replace('class="call"', 'class="contact-bar-btn"'), 'https://agency.example/a', max_links=0)
    assert '(Chiama l’agenzia: tel. 02/00000003)' in page['full_text'] and '(tel. 0200000004)' in page['full_text']
    from app.services.scout import _condition_supported
    assert _condition_supported('renovated', 'gli spazi interni sono stati interessati da una ristrutturazione')
    assert not _condition_supported('renovated', 'Lo Stabile è Di Recente Ristrutturazione')


async def test_reachable_contact_replaces_a_bare_structured_seller(settings):
    page = (PAGES / 'affiliate_hq_footer.html').read_text().replace('</title>', '</title><script type="application/ld+json">'
        '{"@type":"RealEstateListing","name":"Casa in vendita - Via Esempio 4","offers":{"@type":"Offer","price":"279000","priceCurrency":"EUR","seller":{"@type":"RealEstateAgent","name":"Gruppo Test"}}}</script>')
    transport, _ = model_transport({'extract': {**BASE, 'price': 279000, 'advertiser': {'organization': 'Agenzia Ripamonti Test', 'telephone': '02/00000003'}}})
    url = 'https://agency.example/annuncio/1'
    listing = await extract(ScoutModel(scout_settings(settings), transport), page, url, extract_listing(page, url))
    assert listing.evidence['decision_facts']['contact']['telephone'] == '0200000003'
