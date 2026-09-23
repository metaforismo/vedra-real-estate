"""Synthetic markup shaped like public DOM; no third-party listings or network."""
import pytest
from app.connectors.parser import extract_listing, discover_links, canonical_url
from app.connectors.portals import presets, portal_for
from app.schemas import SourceInput


def test_presets_require_operator_permission_and_stay_on_public_pages():
    for preset in presets():
        with pytest.raises(ValueError, match='permesso|permessi|diritti|Conferma|at least'):
            SourceInput.model_validate(preset)
        valid = SourceInput.model_validate({**preset, 'permission_confirmed': True,
                                          'permission_note': 'Synthetic authorized test source'})
        assert valid.config.browser_navigation
        assert not valid.config.retain_raw_html
        assert valid.config.max_pages <= 2


@pytest.mark.parametrize('host,path', [('www.immobiliare.it','annunci'),
    ('www.idealista.it','immobile'),('www.casa.it','immobili')])
def test_profiles_do_not_apply_to_unrelated_hosts_or_subpages(host,path):
    assert portal_for(f'https://{host}/{path}/123/')
    assert portal_for(f'https://{host}/{path}/123/foto/') is None
    assert portal_for(f'https://{host}.example/{path}/123/') is None
    assert portal_for(f'https://{host}/agenzie/123/') is None


def test_immobiliare_exact_labels_and_locality():
    record = extract_listing('''<h1>Trilocale via Esempio, Centro, Como</h1>
        <button><span class="LocationInfo_location__abc">Como</span>
        <span class="LocationInfo_location__abc">Centro</span>
        <span class="LocationInfo_location__abc">Via Esempio</span></button>
        <dl><dt>Prezzo al m²</dt><dd>4.000 €/m²</dd><dt>Prezzo</dt><dd>€ 400.000</dd>
        <dt>Superficie</dt><dd>100 m²</dd><dt>Locali</dt><dd>3</dd>
        <dt>Bagni</dt><dd>2</dd><dt>Contratto</dt><dd>Vendita</dd></dl>
        <div class="ReadAll_readAll__abc">Descrizione sintetica.</div>''',
        'https://www.immobiliare.it/annunci/123/')
    assert (record.price,record.surface,record.city)==(400000,100,'Como')
    assert (record.currency,record.transaction_type,record.property_type)==('EUR','sale','residential')
    assert record.area_basis == 'unknown'
    assert record.evidence['city']['source_url']==record.url


@pytest.mark.parametrize('value',['da € 400.000','400.000 – 600.000 €'])
def test_multiunit_prices_are_not_single_property_values(value):
    with pytest.raises(ValueError,match='più unità'):
        extract_listing(f'<h1>Appartamenti in vendita</h1><dt>Prezzo</dt><dd>{value}</dd>',
                        'https://www.immobiliare.it/annunci/124/')


def test_idealista_uses_property_city_not_search_or_agency():
    record=extract_listing('''<h1>Bilocale in vendita in Via Esempio, 2</h1>
        <span class="info-data-price">240.000 €</span><div class="adCommentsLanguage"><p>Casa luminosa.</p></div>
        <div class="details-property_features"><ul><li>60 m² commerciali</li><li>2 locali</li>
        <li>1 bagno</li><li>Nuova costruzione</li></ul></div>
        <div id="headerMap"><ul><li>Via Esempio, 2</li><li>Rozzano</li><li>Milano Sud, Milano</li></ul></div>
        <a href="/vendita-case/rozzano-milano/">&#xe001; Case a Rozzano</a>
        <aside>Agente di Milano</aside>''','https://www.idealista.it/immobile/456/')
    assert (record.price,record.surface,record.city)==(240000,60,'Rozzano')
    assert (record.condition,record.area_basis)==('new','commercial')
    assert record.zone==''


def test_casa_uses_detail_values_not_mortgage_or_optional_garage():
    record=extract_listing('''<main><h1>Quadrilocale in Vendita in Via Esempio a Como</h1><p>Centro</p>
        <p class="csapdp-infos__price">€ 510.000 <button>tua da € 1500/mese</button></p>
        <p aria-label="Superficie: 120 metri quadri">120 m²</p><p aria-label="Numero di locali: 4">4 locali</p>
        <p aria-label="Numero di bagni: 2">2 bagni</p><p class="chars__lbl">Condizioni immobile</p><p>da ristrutturare</p>
        <div aria-label="Descrizione dell'immobile">Descrizione della casa.</div>
        <p class="map__head--addrs">Via Esempio 2, Como (CO)</p>
        <div aria-label="Galleria immagini, planimetrie e altri media"><img src="https://images.example/house.jpg"></div>
        <p>Box opzionale € 30.000</p></main>''','https://www.casa.it/immobili/789/')
    assert (record.price,record.surface,record.city,record.zone)==(510000,120,'Como','Centro')
    assert record.condition=='to_renovate'
    assert record.images==['https://images.example/house.jpg']
    assert record.availability=='unknown'


def test_no_city_is_invented_when_location_is_missing():
    record=extract_listing('<h1>Appartamento in vendita</h1><span class="info-data-price">300.000 €</span>',
                           'https://www.idealista.it/immobile/457/')
    assert record.city==''
    assert record.surface is None


def test_related_jsonld_cannot_fill_in_missing_property_city():
    record=extract_listing('''<h1>Appartamento in vendita</h1><span class="info-data-price">300.000 €</span>
        <script type="application/ld+json">{"@type":"Apartment","url":"/immobile/999/",
        "address":{"addressLocality":"Milano"},"floorSize":{"value":100},"description":"Altra casa"}</script>''',
        'https://www.idealista.it/immobile/457/')
    assert record.city==''
    assert record.surface is None


def test_casa_discovery_deduplicates_gallery_and_paginates():
    cfg=next(p['config'] for p in presets() if p['name']=='Casa.it')
    links,nxt=discover_links('''<a href="/immobili/12/">Foto</a><a href="/immobili/12/">Titolo</a>
        <a href="https://other.example/immobili/34/">Fuori sito</a>
        <a aria-label="Pagina successiva" href="?page=2">Avanti</a>''',cfg['search_url'],cfg)
    assert links==['https://www.casa.it/immobili/12/']
    assert nxt.endswith('?page=2')


def test_portal_tracking_and_subpages_do_not_create_duplicate_properties():
    cfg=presets()[0]['config']
    html='''<a href="/annunci/12?__nc__fp">Casa</a><a href="/annunci/12/">Foto</a>
        <a href="/annunci/12/foto/">Galleria</a><a href="?pag=2">Successiva</a>'''
    links,nxt=discover_links(html,cfg['search_url'],cfg)
    assert links==['https://www.immobiliare.it/annunci/12/']
    assert nxt.endswith('?pag=2')
    assert canonical_url(links[0]+'?utm_source=test')==links[0]


def test_presets_api_does_not_create_or_enable_sources(api):
    app,client,_=api
    before=client.get('/api/sources').json()
    response=client.get('/api/source-presets')
    assert response.status_code==200
    assert len(response.json())==3
    assert all(not p['permission_confirmed'] for p in response.json())
    assert client.get('/api/sources').json()==before


def test_browser_candidates_include_visible_card_context_for_hermes():
    from bs4 import BeautifulSoup
    from app.services.origination import Origination
    html='<li role="button"><strong>€ 550.000</strong><a href="/annunci/12/">Trilocale</a><span>Milano · 90 m²</span></li>'
    candidates=Origination.page_candidates(BeautifulSoup(html,'html.parser'),
        'https://www.immobiliare.it/vendita-case/milano/', ['https://www.immobiliare.it/annunci/12/'])
    assert '550.000' in candidates[0]['source_text_hint']
    assert 'Milano' in candidates[0]['source_text_hint']
