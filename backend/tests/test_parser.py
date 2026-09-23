import json
import pytest
from pydantic import ValidationError
from app.connectors.parser import number,extract_listing,discover_links,canonical_url
from app.schemas import Listing,SourceInput,Criteria,AgentInput

@pytest.mark.parametrize('raw,expected',[(850000,850000),('€ 850.000',850000),('1.250.000,50',1250000.5),('1,250,000.50',1250000.5),('620,25 mq',620.25),('620,000',620),(' 123.45 ',123.45),('Prezzo su richiesta',None),(None,None),(False,None),(float('nan'),None),(float('inf'),None),('-500',None),('€ −500',None),('(500)',None),(0,None)])
def test_numeric_normalization(raw,expected):
    assert number(raw)==expected


def html(**overrides):
    node={'@context':'https://schema.org','@type':'Apartment','name':'Immobile dimostrativo',
          'description':'Appartamento da ristrutturare.',
          'offers':{'price':250000,'priceCurrency':'EUR','businessFunction':'http://purl.org/goodrelations/v1#Sell'},
          'floorSize':{'value':100,'unitCode':'MTK'},
          'address':{'streetAddress':'Via Esempio 1','addressLocality':'Milano'},
          'additionalProperty':[{'name':'zone','value':'Zona Test'},{'name':'condition','value':'da ristrutturare'},
                                {'name':'area_basis','value':'commerciale'}]}
    node.update(overrides)
    return '<script type="application/ld+json">'+json.dumps(node)+'</script>'


def test_jsonld_complete():
    p=extract_listing(html(),'https://catalog.example/immobile/1?utm_source=x')
    assert p.price==250000 and p.surface==100 and p.city=='Milano'
    assert p.property_type=='residential' and p.condition=='to_renovate'
    assert p.area_basis=='commercial' and p.transaction_type=='sale'
    assert p.url=='https://catalog.example/immobile/1' and not p.is_demo
    assert p.evidence['price']['method']=='json-ld'


def test_unknowns_are_not_invented():
    p=extract_listing(html(offers={'price':250000},additionalProperty=[],address={}), 'https://catalog.example/p/1')
    assert p.currency=='XXX' and p.transaction_type=='unknown' and p.area_basis=='unknown'
    assert p.city=='' and p.address is None


def test_non_square_meters_rejected():
    p=extract_listing(html(floorSize={'value':200,'unitCode':'FTK'}),'https://catalog.example/p/1')
    assert p.surface is None


def test_css_and_currency_evidence():
    p=extract_listing('<h1>Ufficio</h1><b class="price">€ 950.000</b><b class="sqm">510 mq</b><i>vendita</i>',
      'https://catalog.example/p/1',{'price':'.price','surface':'.sqm','transaction_type':'i'})
    assert (p.price,p.surface,p.currency,p.transaction_type)==(950000,510,'EUR','sale')
    assert p.evidence['price']['method']=='css: .price'


def test_no_price_is_not_zero():
    p=extract_listing(html(offers={}), 'https://catalog.example/p/1')
    assert p.price is None


def test_rental_is_not_sale():
    p=extract_listing(html(offers={'price':1500,'priceCurrency':'EUR','businessFunction':'https://example.org/LeaseOut'}), 'https://catalog.example/p/1')
    assert p.transaction_type=='rent'


def test_generic_page_is_not_listing():
    with pytest.raises(ValueError):extract_listing('<h1>Benvenuti</h1>', 'https://catalog.example/')


def test_links_are_scoped_and_normalized():
    text='<a href="/p/1?utm_source=test">1</a><a href="/p/1">1b</a><a href="https://evil.example/p/2">x</a><a href="/privacy">P</a><a class="next" href="/search?page=2">next</a>'
    links,nxt=discover_links(text,'https://catalog.example/search',{'listing_url_pattern':'/p/','next_selector':'.next'})
    assert links==['https://catalog.example/p/1'] and nxt=='https://catalog.example/search?page=2'


def test_jsonld_itemlist_links():
    text='<script type="application/ld+json">'+json.dumps({'@type':'ItemList','itemListElement':[{'@type':'ListItem','url':'/p/7'}]})+'</script>'
    assert discover_links(text,'https://catalog.example/search',{'listing_url_pattern':'/p/'})[0]==['https://catalog.example/p/7']


def test_canonical_keeps_identity_params():
    assert canonical_url('https://CATALOG.example/p?id=42&utm_source=a#photo')=='https://catalog.example/p?id=42'

@pytest.mark.parametrize('field,value',[('price',-1),('surface',float('nan')),('latitude',95),('url','javascript:alert(1)')])
def test_invalid_listing_rejected(field,value):
    raw={'listing_key':'1','url':'https://catalog.example/p/1','title':'Test',field:value}
    with pytest.raises(ValidationError):Listing(**raw)


def test_images_scheme_filter():
    p=Listing(listing_key='1',url='https://catalog.example/p/1',title='Test',images=['javascript:x','file:///etc/passwd','https://catalog.example/a.png'])
    assert p.images==['https://catalog.example/a.png']


def test_agent_bounds():
    with pytest.raises(ValidationError):AgentInput(name='Test',city='Milano',source_ids=['a'],interval_minutes=2)
    with pytest.raises(ValidationError):Criteria(min_surface=100,max_surface=50)


def test_source_requires_permission():
    with pytest.raises(ValidationError):SourceInput(name='Test',domain='catalog.example',config={'search_url':'https://catalog.example/search'},permission_note='Documentazione dei permessi',permission_confirmed=False)


@pytest.mark.parametrize('condition,expected',[
    ('RISTRUTTURATO','good'),('OTTIME CONDIZIONI, RISTRUTTURATO 2019','good'),
    ('ristrutturata nel 2020','good'),('Nuova costruzione','new'),
    ('Non ristrutturato','unknown'),('da ristrutturare','to_renovate'),
    ('Parzialmente ristrutturato','unknown'),('ristrutturato da verificare','unknown'),
])
def test_condition_labels_keep_source_evidence(condition,expected):
    p=extract_listing('<h1>Immobile</h1><b>€ 550.000</b><i>'+condition+'</i>',
                      'https://catalog.example/p/1',{'price':'b','condition':'i'})
    assert p.condition==expected
    assert p.evidence['condition']['value']==condition


def test_gallery_and_single_published_marker():
    raw="""<h1>Test</h1><b>€ 200000</b><div class="wdk-map"></div>
    <img class="gallery" src="/photo.jpg"><img class="gallery" src="/photo.jpg"><img src="/logo.png">
    <script>wdk_generate_marker_basic_popup('45.5','9.5',anything);</script>"""
    p=extract_listing(raw,'https://catalog.example/p/1',{'price':'b','images':'img.gallery'})
    assert p.images==['https://catalog.example/photo.jpg']
    assert (p.latitude,p.longitude)==(45.5,9.5)
    assert 'precision unverified' in p.evidence['latitude']['method']
    p=extract_listing(raw+"<script>wdk_generate_marker_basic_popup('46','10',anything);</script>",'https://catalog.example/p/1',{'price':'b'})
    assert p.latitude is None

@pytest.mark.parametrize('locality,city,zone',[
    ('Milano Zona Navigli','Milano','Navigli'),
    ('Reggio di Calabria ZONA Centro','Reggio di Calabria','Centro'),
    ('Milano Marittima Zona Centro','Milano Marittima','Centro'),
    ('Milano Navigli','',''),
])
def test_explicit_locality_heading_requires_separator(locality,city,zone):
    p=extract_listing(f'<h1>Appartamento</h1><b>€ 550.000</b><h4>{locality}</h4>',
        'https://catalog.example/p/1',{'price':'b','locality':'h4'})
    assert p.city==city and p.zone==zone
    if city:assert p.evidence['city']['value']==locality

@pytest.mark.parametrize('status,expected',[
    ('Venduto','sold'),('Affittato','rented'),('Ritirato','withdrawn'),
    ('Non ancora venduto','unknown'),('Libero','unknown'),
])
def test_source_status_label_is_not_guessed(status,expected):
    p=extract_listing(f'<h1>Appartamento</h1><b>€ 550.000</b><i>{status}</i>',
        'https://catalog.example/p/1',{'price':'b','availability':'i'})
    assert p.availability==expected
    if expected!='unknown':assert p.evidence['availability']['value']==status


def test_locality_does_not_override_structured_address():
    p=extract_listing(html()+'<h4>Como Zona Centro</h4>',
        'https://catalog.example/p/1',{'locality':'h4'})
    assert p.city=='Milano' and p.zone=='Zona Test'
