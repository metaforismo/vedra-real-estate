"""Public-page adapters. They never change transport, cookies or access checks."""
from copy import deepcopy
import re
from urllib.parse import urlsplit


PORTALS = {
    'www.immobiliare.it': {
        'name': 'Immobiliare.it', 'path': '/annunci/',
        'search_url': 'https://www.immobiliare.it/vendita-case/milano/',
        'next_selector': 'a:-soup-contains-own("Successiva")',
        'fields': {
            'transaction_type': 'dt:-soup-contains-own("Contratto") + dd',
            'property_type': 'dt:-soup-contains-own("Tipologia") + dd',
            'description': '[class*="ReadAll_readAll__"]',
        },
    },
    'www.idealista.it': {
        'name': 'idealista', 'path': '/immobile/',
        'search_url': 'https://www.idealista.it/vendita-case/milano-milano/',
        'next_selector': 'a:-soup-contains-own("Successiva")',
        'fields': {'price': '.info-data-price', 'description': '.adCommentsLanguage p'},
    },
    'www.casa.it': {
        'name': 'Casa.it', 'path': '/immobili/',
        'search_url': 'https://www.casa.it/vendita/residenziale/milano/',
        'next_selector': 'a[aria-label="Pagina successiva"]',
        'fields': {
            'price': '.csapdp-infos__price',
            'surface': 'main [aria-label^="Superficie:"]',
            'rooms': 'main [aria-label^="Numero di locali:"]',
            'bathrooms': 'main [aria-label^="Numero di bagni:"]',
            'description': '[aria-label="Descrizione dell\'immobile"]',
            'condition': '.chars__lbl:-soup-contains-own("Condizioni immobile") + p',
            'images': '[aria-label="Galleria immagini, planimetrie e altri media"] img',
        },
    },
}


def portal_for(url):
    parts = urlsplit(url)
    profile = PORTALS.get(parts.hostname)
    # Exclude agency pages, promotions' subpages and unrelated linked content.
    return profile if profile and re.fullmatch(re.escape(profile['path']) + r'\d+/?', parts.path) else None


def presets():
    return [{'name': p['name'], 'domain': host, 'permission_note': '',
             'permission_confirmed': False, 'config': {
                 'search_url': p['search_url'], 'probe_city': 'Milano',
                 'listing_selector': f'a[href*="{p["path"]}"]',
                 'listing_url_pattern': p['path'], 'next_selector': p['next_selector'],
                 'max_pages': 2, 'browser_navigation': True, 'retain_raw_html': False,
                 'retain_images': True, 'detail_refresh_hours': 6, 'fields': {},
             }} for host, p in PORTALS.items()]


def field_defaults(url):
    profile = portal_for(url)
    return deepcopy(profile['fields']) if profile else {}


def enrich(soup, url, record, clean, number, normalize_condition):
    """Only explicit DOM labels; never infer city from the search or agency address."""
    profile = portal_for(url)
    if not profile:
        return
    host = urlsplit(url).hostname
    price_node = soup.select_one(profile['fields'].get('price', 'dt + dd'))
    if host != 'www.immobiliare.it' and price_node:
        price_text = clean(price_node.get_text(' ', strip=True))
        if re.match(r'^(?:da|a partire da)\b', price_text, re.I) or re.search(r'\d\s*[-–]\s*\d', price_text):
            raise ValueError('Annuncio con più unità o intervallo di valori: verifica le singole schede.')

    def put(key, value, origin):
        if value not in (None, '', 'unknown'):
            record[key] = value
            record['evidence'][key] = {'method': f'portal DOM: {origin}', 'value': value, 'source_url': url}

    title = soup.select_one('h1')
    title = clean(title.get_text(' ', strip=True)) if title else ''
    put('title', title, 'h1')
    if re.search(r'\bin vendita\b', title, re.I):
        put('transaction_type', 'sale', 'h1: in vendita')
    elif re.search(r'\bin affitto\b', title, re.I):
        put('transaction_type', 'rent', 'h1: in affitto')
    if re.match(r'^(?:(?:mono|bi|tri|quadri|penta)locale|appartamento|attico|villa)\b', title, re.I):
        put('property_type', 'residential', 'h1: tipologia')

    if host == 'www.immobiliare.it':
        parts = soup.select('button [class*="LocationInfo_location__"]')
        if len(parts) == 3:
            for key, node in zip(('city', 'zone', 'address'), parts):
                put(key, clean(node.get_text()), 'LocationInfo')
        # Match complete labels: "Prezzo al m²" is not the asking price.
        labels = {'Prezzo': 'price', 'Superficie': 'surface', 'Locali': 'rooms', 'Bagni': 'bathrooms'}
        for label, key in labels.items():
            term = next((d for d in soup.select('dt') if clean(d.get_text()) == label), None)
            value = term.find_next_sibling('dd') if term else None
            if value:
                text = clean(value.get_text())
                if re.match(r'^da\b', text, re.I) or re.search(r'\d\s*[-–]\s*\d', text):
                    raise ValueError('Annuncio con più unità o intervallo di valori: verifica le singole schede.')
                put(key, number(text), f'dt: {label}')
                if key == 'price' and '€' in text:
                    put('currency', 'EUR', 'dt: Prezzo')
    elif host == 'www.casa.it':
        address = soup.select_one('.map__head--addrs')
        text = clean(address.get_text()) if address else ''
        location = re.fullmatch(r'(.+),\s*([^,]+)\s+\([A-Z]{2}\)', text)
        if location:
            put('address', location[1], '.map__head--addrs')
            put('city', location[2], '.map__head--addrs')
        subtitle = soup.select_one('h1 + p')
        if subtitle:
            put('zone', clean(subtitle.get_text()), 'h1 + p')
    else:
        city_links = {clean(a.get_text()).split('Case a ', 1)[1].strip()
                      for a in soup.select('a[href^="/vendita-case/"],a[href^="/affitto-case/"]')
                      if clean(a.get_text()).lstrip('\ue001 ').startswith('Case a ')}
        if len(city_links) == 1:
            put('city', city_links.pop(), 'link Case a')
        address = soup.select_one('#headerMap li')
        if address:
            put('address', clean(address.get_text()), '#headerMap li')
        for node in soup.select('.details-property_features li'):
            text = clean(node.get_text())
            if re.fullmatch(r'[\d.,]+\s*m²\s+commerciali', text):
                put('surface', number(text), 'caratteristiche: m² commerciali')
                put('area_basis', 'commercial', 'caratteristiche: m² commerciali')
            elif re.fullmatch(r'\d+\s+local[ei]', text):
                put('rooms', number(text), 'caratteristiche: locali')
            elif re.fullmatch(r'\d+\s+bagn[oi]', text):
                put('bathrooms', number(text), 'caratteristiche: bagni')
            else:
                put('condition', normalize_condition(text), 'caratteristiche: stato')
