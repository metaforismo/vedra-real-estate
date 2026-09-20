from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, urljoin

from bs4 import BeautifulSoup

from ..schemas import Listing

PARSER_VERSION='jsonld-css/1.1'
TYPE_MAP={'apartment':'residential','house':'residential','singlefamilyresidence':'residential',
          'residence':'residential','residential':'residential','appartamento':'residential',
          'villa':'residential','ufficio':'office','office':'office','negozio':'commercial',
          'commerciale':'commercial','commercial':'commercial','capannone':'logistics',
          'logistics':'logistics','terreno':'land','land':'land','hotel':'hospitality','hospitality':'hospitality'}
CONDITION_MAP={'nuovo':'new','new':'new','buono':'good','buono stato':'good','good':'good',
               'ottimo':'good','da ristrutturare':'to_renovate','to_renovate':'to_renovate','grezzo':'shell','shell':'shell'}
CONDITION_MAP.update({'ristrutturato':'good','ristrutturata':'good','ottime condizioni':'good',
                      'ottimo stato':'good','buone condizioni':'good','nuova costruzione':'new',
                      'da ristrutturare completamente':'to_renovate'})


def normalize_condition(value: str) -> str:
    text=clean(value).casefold()
    if text in CONDITION_MAP:
        return CONDITION_MAP[text]
    # Only normalize explicit condition labels, never claims from arbitrary prose.
    if re.fullmatch(r'(?:ottime condizioni\s*,\s*)?ristrutturat[oa](?:\s+(?:nel\s+)?\d{4})?',text):
        return 'good'
    return 'unknown'


def clean(value) -> str:
    if value is None:
        return ''
    return re.sub(r'\s+',' ',BeautifulSoup(str(value),'html.parser').get_text(' ',strip=True)).strip()


def number(value) -> float | None:
    """Italian amounts and JSON numeric values; never turn an absent value into 0."""
    if value is None or isinstance(value,bool):
        return None
    if isinstance(value,(int,float)):
        return float(value) if 0<float(value)<1e12 else None
    text=str(value).strip().replace('\xa0',' ')
    match=re.search(r'\d[\d.,\s]*',text)
    if not match:
        return None
    if text[:match.start()].rstrip().endswith(('-', '−', '(')):
        return None
    n=re.sub(r'\s+','',match.group())
    if ',' in n and '.' in n:
        n=n.replace('.','').replace(',','.') if n.rfind(',')>n.rfind('.') else n.replace(',','')
    elif ',' in n:
        n=n.replace(',','.')  # Italian comma is decimal, including three decimal places.
    elif re.fullmatch(r'\d{1,3}(\.\d{3})+',n):
        n=n.replace('.','')
    try:
        v=float(n)
        return v if 0<v<1e12 else None
    except ValueError:
        return None


def canonical_url(url: str) -> str:
    p=urlsplit(url)
    params=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','gclid')]
    return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path or '/',urlencode(sorted(params)),''))


def list_nodes(value):
    if isinstance(value,list):
        for node in value:
            yield from list_nodes(node)
    elif isinstance(value,dict):
        yield value
        for key in ('@graph','mainEntity','itemListElement','item','itemOffered','about'):
            if key in value:
                yield from list_nodes(value[key])


def jsonld_nodes(soup):
    for element in soup.select('script[type="application/ld+json"]'):
        try:
            yield from list_nodes(json.loads(element.string or element.get_text()))
        except (json.JSONDecodeError,TypeError,RecursionError):
            continue


def first(value):
    return value[0] if isinstance(value,list) and value else value


def extract_listing(html: str, url: str, fields: dict[str,str] | None=None, *, is_demo=False) -> Listing:
    soup=BeautifulSoup(html,'html.parser')
    url=canonical_url(url)
    record={'url':url,'listing_key':hashlib.sha256(url.encode()).hexdigest()[:24],'evidence':{},'is_demo':is_demo}
    fields=fields or {}
    nodes=list(jsonld_nodes(soup))
    candidates=[]
    for node in nodes:
        types=node.get('@type',[])
        types=[types] if isinstance(types,str) else types
        if any(t.lower() in {*TYPE_MAP,'realestatelisting','product','accommodation','place'} for t in types):
            weight=sum(k in node for k in ('offers','floorSize','address','description','price','numberOfRooms'))
            candidates.append((weight,node))
    chosen=max(candidates,key=lambda x:x[0])[1] if candidates else {}
    # Listing wrappers can hold offers outside the residential mainEntity.
    wrappers=[n for n in nodes if n.get('@type')=='RealEstateListing']
    offer=first(chosen.get('offers',{})) or {}
    if not isinstance(offer,dict): offer={}
    if not offer and wrappers:
        offer=first(wrappers[0].get('offers',{})) or {}
    address=chosen.get('address',{})
    address=address if isinstance(address,dict) else {'streetAddress':clean(address)}
    floor=chosen.get('floorSize',{})
    floor=floor if isinstance(floor,dict) else {'value':floor}
    geo=chosen.get('geo',{})
    geo=geo if isinstance(geo,dict) else {}
    raw_type=first(chosen.get('@type',[])) or ''
    mapped=TYPE_MAP.get(raw_type.lower(),'unknown')
    structured={
        'title':clean(chosen.get('name')),
        'description':clean(chosen.get('description')),
        'price':number(offer.get('price',chosen.get('price'))),
        'surface':number(floor.get('value')) if floor.get('unitCode','MTK') in ('MTK','M2','m2','m²') else None,
        'address':clean(address.get('streetAddress')) or None,
        'city':clean(address.get('addressLocality')),
        'rooms':number(chosen.get('numberOfRooms')),
        'bathrooms':number(chosen.get('numberOfBathroomsTotal')),
        'property_type':mapped,
    }
    for key,value in structured.items():
        if value not in (None,'','unknown'):
            record[key]=value
            record['evidence'][key]={'method':'json-ld','value':value,'source_url':url}
    if offer.get('priceCurrency') and re.fullmatch('[A-Z]{3}',str(offer['priceCurrency'])):
        record['currency']=offer['priceCurrency']
        record['evidence']['currency']={'method':'json-ld priceCurrency','value':record['currency'],'source_url':url}
    business = str(offer.get('businessFunction','')).lower().rsplit('#',1)[-1].rsplit('/',1)[-1]
    operation = {'sell':'sale','leaseout':'rent'}.get(business)
    if operation:
        record['transaction_type']=operation
        record['evidence']['transaction_type']={'method':'json-ld businessFunction','value':operation,'source_url':url}
    # Explicit semantic fields commonly exposed as schema.org PropertyValue entries.
    additional=chosen.get('additionalProperty',[])
    if isinstance(additional,dict): additional=[additional]
    for prop in additional:
        if not isinstance(prop,dict): continue
        key=str(prop.get('name','')).strip().lower()
        value=clean(prop.get('value'))
        if key in ('zone','area_basis','condition','property_type','transaction_type') and value:
            if key=='property_type': value=TYPE_MAP.get(value.lower(),'unknown')
            if key=='condition': value=normalize_condition(value)
            if key=='area_basis': value={'commercial':'commercial','commerciale':'commercial','net':'net','netta':'net','gross':'gross','lorda':'gross'}.get(value.lower(),'unknown')
            if key=='transaction_type': value={'sale':'sale','vendita':'sale','rent':'rent','affitto':'rent'}.get(value.lower(),'unknown')
            record[key]=value
            record['evidence'][key]={'method':'json-ld additionalProperty','value':value,'source_url':url}
    for key,jsonkey in (('latitude','latitude'),('longitude','longitude')):
        try:
            if geo.get(jsonkey) is not None:
                record[key]=float(geo[jsonkey])
                record['evidence'][key]={'method':'json-ld (precision non verificata)','value':record[key],'source_url':url}
        except (ValueError,TypeError): pass
    images=chosen.get('image',[])
    images=images if isinstance(images,list) else [images]
    record['images']=[urljoin(url,x.get('url','') if isinstance(x,dict) else x) for x in images if isinstance(x,(str,dict))][:30]
    for key,selector in fields.items():
        element=soup.select_one(selector)
        if element is None:
            continue
        text=clean(element.get('content') or element.get_text(' ',strip=True))
        value=number(text) if key in ('price','surface','rooms','bathrooms') else text
        if value is None or value=='':
            continue
        if key=='price' and ('€' in text or 'EUR' in text.upper()):
            record['currency']='EUR'
            record['evidence']['currency']={'method':f'css: {selector} explicit EUR','value':'EUR','source_url':url}
        if key=='currency':
            value={'€':'EUR','euro':'EUR'}.get(text.lower(),text.upper())
            if not re.fullmatch('[A-Z]{3}',value):continue
        if key=='property_type':
            value=TYPE_MAP.get(text.lower(), 'unknown')
            if value=='unknown' and re.match(r'^(?:mono|bi|tri|quadri)local[ei]\b|^appartament[oi]\b',text,re.I):value='residential'
        if key=='condition': value=normalize_condition(text)
        if key=='area_basis':
            value={'commerciale':'commercial','commercial':'commercial','netta':'net','net':'net','lorda':'gross','gross':'gross'}.get(text.lower(),'unknown')
        if key=='transaction_type':
            value={'vendita':'sale','sale':'sale','affitto':'rent','rent':'rent'}.get(text.lower(),'unknown')
        record[key]=value
        record['evidence'][key]={'method':f'css: {selector}','value':text,'source_url':url}
    if not record.get('title'):
        title=soup.select_one('h1')
        if title:
            record['title']=clean(title.get_text())[:500]
            record['evidence']['title']={'method':'h1','value':record['title'],'source_url':url}
    if not record.get('description'):
        meta=soup.select_one('meta[name="description"]')
        if meta:
            record['description']=clean(meta.get('content',''))[:30000]
            record['evidence']['description']={'method':'meta description','value':record['description'],'source_url':url}
    if not record.get('title'):
        raise ValueError('Nessun titolo estratto. Configura i selettori della fonte.')
    # Generic page titles alone are not enough evidence of an actual property.
    if not any(record.get(x) for x in ('price','surface','address')):
        raise ValueError('Pagina non riconosciuta come annuncio: mancano prezzo, superficie e indirizzo.')
    return Listing.model_validate(record)


def discover_links(html: str, url: str, config: dict) -> tuple[list[str],str | None]:
    soup=BeautifulSoup(html,'html.parser')
    links=[]
    domain=urlsplit(url).hostname
    pattern=config.get('listing_url_pattern','')
    for element in soup.select(config.get('listing_selector','a[href]')):
        href=element.get('href')
        if not href:
            continue
        candidate=canonical_url(urljoin(url,href))
        if urlsplit(candidate).hostname!=domain or urlsplit(candidate).scheme not in ('http','https'):
            continue
        # Literal substring, not untrusted arbitrary regex (avoids ReDoS).
        if pattern and pattern not in urlsplit(candidate).path:
            continue
        if candidate not in links:
            links.append(candidate)
    # ItemList links can be useful on search pages with no visible anchors.
    for node in jsonld_nodes(soup):
        if node.get('@type')=='ListItem':
            item=node.get('item')
            candidate=node.get('url') or (item.get('url') if isinstance(item,dict) else None)
            if candidate:
                candidate=canonical_url(urljoin(url,candidate))
                if (urlsplit(candidate).scheme in ('http','https') and urlsplit(candidate).hostname==domain
                    and (not pattern or pattern in urlsplit(candidate).path) and candidate not in links):
                    links.append(candidate)
    next_url=None
    if config.get('next_selector'):
        nxt=soup.select_one(config['next_selector'])
        if nxt and nxt.get('href'):
            candidate=urljoin(url,nxt['href'])
            if urlsplit(candidate).hostname==domain:
                next_url=candidate
    return links,next_url
