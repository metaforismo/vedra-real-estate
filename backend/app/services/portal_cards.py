"""Listing cards from portal alert emails and from results pages a person sends with Vedra Capture.

Both channels carry HTML that a portal produced for a person: Vedra never fetches the portal. The HTML
is untrusted. A link counts only when it resolves to a known portal listing URL; tracker links are decoded
from their own parameters and never opened. Every value is copied from the card text, like Scout's
validation: what is not written stays empty, and an ambiguous card (two prices, two surfaces) keeps none.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, unquote, urljoin, urlsplit

import soupsieve
from bs4 import BeautifulSoup, Tag

from ..connectors.parser import canonical_url, number
from ..connectors.portals import portal_for
from ..db import load, now
from ..schemas import Listing

# URL pattern and results-page card containers per portal. Container classes follow the public markup
# observed on results pages; when they change, the generic walk below still isolates each card.
PORTALS = {
    'immobiliare.it': {'name': 'immobiliare.it', 'host': 'www.immobiliare.it', 'segment': 'annunci',
                       'cards': ('li.nd-list__item', '.in-listingCard', '[class*="ListingCard"]')},
    'idealista.it': {'name': 'idealista', 'host': 'www.idealista.it', 'segment': 'immobile',
                     'cards': ('article.item', 'article[class*="item"]')},
    'casa.it': {'name': 'casa.it', 'host': 'www.casa.it', 'segment': 'immobili',
                'cards': ('article[class*="srp-card"]', '[class*="csaSrpcard"]')},
}
ORIGINS = {'alert': 'Avviso email', 'results_page': 'Pagina dei risultati'}

MONEY = re.compile(r'(?:€|\bEUR)\s?(?P<a>\d{1,3}(?:[.  ]\d{3})+|\d{3,9})(?:,\d{1,2})?'
                   r'|(?P<b>\d{1,3}(?:[.  ]\d{3})+|\d{3,9})(?:,\d{1,2})?\s?(?:€|EUR\b|euro\b)', re.I)
PER_UNIT = re.compile(r'^\s*(?:/|al|a)\s*(?:m²|m2|mq|metro)', re.I)
PER_MONTH = re.compile(r'^\s*(?:/\s*mese|al mese|mensil)', re.I)
NOT_PRICE = re.compile(r'(?:rata|mutuo|finanziam|spese|condomin|caparra|anticipo)[^€\d]{0,25}$', re.I)
SURFACE = re.compile(r'(?<![\d.,])(\d{1,3}(?:\.\d{3})+|\d{1,6})(?:,\d{1,2})?\s?(?:m²|m2\b|mq\b|metri quadr)', re.I)
ROOMS = re.compile(r'(?<![\d.,])(\d{1,2})\s?local[ei]\b', re.I)
BATHS = re.compile(r'(?<![\d.,])(\d{1,2})\s?bagn[io]\b', re.I)
DROP = re.compile(r'ribass|prezzo (?:ridotto|abbassato|sceso|in calo)|calo (?:del|di) prezzo|riduzione (?:del|di) prezzo|'
                  r'nuovo prezzo|ha abbassato|è sceso|[-−–]\s?\d{1,2}(?:,\d)?\s?%', re.I)
STREET = re.compile(r'\b(?:via|viale|v\.le|piazza|p\.za|piazzale|corso|c\.so|largo|vicolo|strada|alzaia|ripa|'
                    r'bastioni|lungarno|lungotevere|contrada)\s+\S.*', re.I)
CITY = re.compile(r'\bin (?:vendita|affitto) a ([A-ZÀ-Ý][\wÀ-ÿ\'’-]+(?:\s+[A-ZÀ-Ý][\wÀ-ÿ\'’-]+){0,3})')
CTA = re.compile(r'^(?:vedi|scopri|guarda|apri|dettagli|visualizza|leggi|contatta|mostra|vai|clicca|salva|more|see)\b', re.I)
NAV = re.compile(r'modific|ricerc|gestisci|avvisi|disiscri|cancella|impostaz|preferenz|privacy|scarica|app\b|tutti gli|condizioni|'
                 r'aiuto|termini|unsubscribe|mailto:|tel:', re.I)
FIELDS = ('title', 'price', 'currency', 'surface', 'rooms', 'bathrooms', 'address', 'zone', 'city', 'property_type', 'transaction_type')
# Provincial capitals: with the comuni of the workspace's searches, benchmarks and OMI cache they are the only
# names accepted as a comune when a card writes its location as "via …, zona, comune" without saying so.
CAPITALS = '''Agrigento Alessandria Ancona Andria Aosta Arezzo Ascoli-Piceno Asti Avellino Bari Barletta Belluno Benevento
Bergamo Biella Bologna Bolzano Brescia Brindisi Cagliari Caltanissetta Campobasso Carbonia Carrara Caserta Catania Catanzaro
Cesena Chieti Como Cosenza Cremona Crotone Cuneo Enna Fermo Ferrara Firenze Foggia Forlì Frosinone Genova Gorizia Grosseto
Imperia Isernia L'Aquila La-Spezia Latina Lecce Lecco Livorno Lodi Lucca Macerata Mantova Massa Matera Messina Milano Modena
Monza Napoli Novara Nuoro Oristano Padova Palermo Parma Pavia Perugia Pesaro Pescara Piacenza Pisa Pistoia Pordenone Potenza
Prato Ragusa Ravenna Reggio-Calabria Reggio-Emilia Rieti Rimini Roma Rovigo Salerno Sassari Savona Siena Siracusa Sondrio
Taranto Teramo Terni Torino Trani Trapani Trento Treviso Trieste Udine Urbino Varese Venezia Verbania Vercelli Verona
Vibo-Valentia Vicenza Viterbo'''
CAPITALS = [name.replace('-', ' ') for name in CAPITALS.split()]


@dataclass
class Card:
    url: str
    portal: str
    listing_id: str
    title: str
    text: str
    price: float | None = None
    old_price: float | None = None
    price_drop: bool = False
    currency: str | None = None
    surface: float | None = None
    rooms: float | None = None
    bathrooms: float | None = None
    address: str | None = None
    zone: str = ''
    city: str = ''
    transaction_type: str = 'unknown'
    property_type: str = 'unknown'
    image: str | None = None
    quotes: dict = field(default_factory=dict)
    how: dict = field(default_factory=dict)


def _squash(value: str) -> str:
    return ' '.join(str(value).split())


def _text(node: Tag) -> str:
    return _squash(node.get_text(' '))


def portal_key(host: str) -> str | None:
    host = (host or '').lower().rstrip('.')
    return next((k for k in PORTALS if host == k or host.endswith('.' + k)), None)


def _decoded(value: str):
    """Candidate URLs written inside a tracker link: percent-encoded or base64, never followed."""
    for _ in range(3):
        if re.match(r'https?://', value, re.I):
            yield value
            return
        if '%' not in value:
            break
        value = unquote(value)
    token = value.strip()
    if len(token) >= 16 and re.fullmatch(r'[A-Za-z0-9_\-+/]+={0,2}', token):
        try:
            text = base64.urlsafe_b64decode(token.replace('+', '-').replace('/', '_') + '=' * (-len(token) % 4)).decode('utf-8')
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return
        if re.match(r'https?://', text, re.I):
            yield text


def _embedded(href: str, parts):
    for query in (parts.query, parts.fragment):
        for _, value in parse_qsl(query, keep_blank_values=False):
            yield from _decoded(value)
    for segment in parts.path.split('/'):
        if segment:
            yield from _decoded(segment)
    # A destination written in the path ("/click/https%3A%2F%2F…") survives the segment split only whole.
    text = unquote(unquote(href))
    for match in re.finditer(r'https?://[^\s"\'<>]+', text[1:]):
        yield match.group()


def listing_link(href: str, base: str | None = None, _depth: int = 0) -> tuple[str, str, str] | None:
    """(canonical listing URL, portal key, listing id) when href is, or wraps, a portal listing URL."""
    if not href or _depth > 3 or len(href) > 4000:
        return None
    href = href.strip()
    try:
        if base:
            href = urljoin(base, href)
        parts = urlsplit(href)
    except ValueError:
        return None
    if parts.scheme.lower() not in ('http', 'https') or parts.username or parts.password:
        return None
    key = portal_key(parts.hostname or '')
    if key:
        segment = PORTALS[key]['segment']
        match = re.match(r'^(?:/[a-z]{2})?/' + segment + r'/(\d{4,12})(?:/|$)', parts.path)
        if match:
            url = canonical_url(f"https://{PORTALS[key]['host']}/{segment}/{match[1]}/")
            if portal_for(url):
                return url, key, match[1]
    for candidate in _embedded(href, parts):
        found = listing_link(candidate, None, _depth + 1)
        if found:
            return found
    return None


def _struck(root: Tag) -> str:
    nodes = root.select('s,del,strike,[style*="line-through"]')
    return ' '.join(_text(n) for n in nodes)


def _amounts(text: str) -> list[tuple[float, str, bool]]:
    """Asking-price amounts written in the text: (value, quote, per month). Per-m² and instalments excluded."""
    found = []
    for match in MONEY.finditer(text):
        after, before = text[match.end():match.end() + 16], text[max(0, match.start() - 40):match.start()]
        if PER_UNIT.match(after) or NOT_PRICE.search(before):
            continue
        value = number(match.group('a') or match.group('b'))
        if value:
            found.append((value, match.group().strip(), bool(PER_MONTH.match(after))))
    return found


def _single(pattern: re.Pattern, text: str) -> tuple[float | None, str | None]:
    values = {}
    for match in pattern.finditer(text):
        value = number(match.group(1))
        if value is not None:
            values.setdefault(value, match.group().strip())
    return next(iter(values.items())) if len(values) == 1 else (None, None)


def _signature(node) -> tuple:
    text = _text(node) if isinstance(node, Tag) else ''
    return (frozenset(v for v, _, _ in _amounts(text)), frozenset(number(m[1]) for m in SURFACE.finditer(text)))


def _card_root(anchor: Tag, url: str, link_of: dict, selectors: tuple) -> Tag:
    urls_in = lambda node: {link_of[id(a)] for a in node.find_all('a', href=True) if id(a) in link_of}
    for parent in anchor.parents:
        if parent.name in ('body', 'html', '[document]'):
            break
        if any(soupsieve.match(sel, parent) for sel in selectors) and urls_in(parent) == {url}:
            return parent
    # Generic walk: the largest block that still holds this listing only, and stops growing once the
    # next level would add another price or surface (the header of the email, another card).
    best = anchor
    for parent in anchor.parents:
        if parent.name in ('body', 'html', '[document]') or len(_text(parent)) > 2500:
            break
        if urls_in(parent) != {url}:
            break
        signature = _signature(best)
        if any(signature) and _signature(parent) != signature:
            break
        best = parent
    return best


def _title(anchors: list[Tag], root: Tag, portal: str, ident: str) -> tuple[str, str]:
    texts = [_text(a) for a in anchors]
    texts = [t for t in texts if 6 <= len(t) <= 200 and not CTA.match(t) and not MONEY.fullmatch(t)
             and not re.match(r'(?:https?://|www\.)', t, re.I) and re.search(r'[A-Za-zÀ-ÿ]{3}', t)]
    if texts:
        return max(texts, key=len), 'testo del link'
    for node in root.select('h1,h2,h3,h4,h5,h6,strong,b'):
        text = _text(node)
        if 8 <= len(text) <= 200 and not MONEY.search(text) and re.search(r'[A-Za-zÀ-ÿ]{3}', text):
            return text, 'titolo della scheda'
    for anchor in anchors:
        img = anchor.find('img', alt=True)
        if img and 6 <= len(_squash(img['alt'])) <= 200:
            return _squash(img['alt']), 'testo alternativo della foto'
    # Required by the schema: a label built only from the portal and the id in the link, not a description.
    return f'Annuncio {PORTALS[portal]["name"]} n. {ident}', 'identificativo nel link'


def _card(root: Tag, anchors: list[Tag], url: str, portal: str, ident: str) -> Card:
    text = _text(root)[:3000]
    title, title_method = _title(anchors, root, portal, ident)
    card = Card(url=url, portal=portal, listing_id=ident, title=title[:200], text=text)
    card.quotes['title'] = title_method
    amounts = _amounts(text)
    distinct = list(dict.fromkeys(v for v, _, _ in amounts))
    quote = {v: q for v, q, _ in reversed(amounts)}
    struck = {v for v, _, _ in _amounts(_struck(root))}
    drop = bool(DROP.search(text))
    if len(distinct) == 1 and distinct[0] not in struck:
        card.price = distinct[0]
    elif len(distinct) == 2:
        old = [v for v in distinct if v in struck]
        if len(old) == 1:
            card.old_price, card.price = old[0], next(v for v in distinct if v != old[0])
        elif drop:
            card.old_price, card.price = max(distinct), min(distinct)
    if card.price is not None:
        card.quotes['price'] = quote[card.price]
        card.currency = 'EUR'
        if any(v == card.price and monthly for v, _, monthly in amounts):
            card.transaction_type = 'rent'
    if card.old_price is not None:
        card.quotes['old_price'] = quote[card.old_price]
    card.price_drop = drop or (card.old_price is not None and card.price is not None and card.price < card.old_price)
    card.surface, card.quotes['surface'] = _single(SURFACE, text)
    card.rooms, card.quotes['rooms'] = _single(ROOMS, text)
    card.bathrooms, card.quotes['bathrooms'] = _single(BATHS, text)
    # Location is read line by line (each text node), never across the flattened card.
    segments = [title, *(_squash(x) for x in root.stripped_strings)]
    for segment in segments:
        street = STREET.search(segment)
        if street and not MONEY.search(street.group()):
            card.address = street.group().split(' · ')[0].strip(' ,.-')[:160]
            card.quotes['address'] = card.address
            break
    for segment in segments:
        city = CITY.search(segment)
        if city:
            words = city[1].split()
            cut = next((i for i, w in enumerate(words) if STREET.match(w + ' x')), len(words))
            if cut:
                card.city = ' '.join(words[:cut])[:100]
                card.quotes['city'] = segment[:160]
                break
    # Same rule as the portal detail parser: a residential type only when the title opens with it.
    kind = re.match(r'^(?:(?:mono|bi|tri|quadri|penta)locale|appartamento|attico|villa)\b', title, re.I)
    if kind:
        card.property_type, card.quotes['property_type'] = 'residential', kind.group()
    words = {w for w in ('vendita', 'affitto') if re.search(r'\b' + w + r'\b', text, re.I)}
    if card.transaction_type == 'unknown' and len(words) == 1:
        card.transaction_type = 'sale' if words == {'vendita'} else 'rent'
    for img in root.find_all('img', src=True):
        src = img['src'].strip()
        # Reference only: never downloaded. Tracking pixels are left out.
        if re.match(r'https://', src, re.I) and img.get('width') not in ('1', '0') and img.get('height') not in ('1', '0'):
            card.image = src[:1000]
            break
    card.quotes = {k: v for k, v in card.quotes.items() if v}
    return card


def _norm(name: str) -> str:
    text = unicodedata.normalize('NFKD', str(name)).encode('ascii', 'ignore').decode()
    return ' '.join(text.replace('’', "'").casefold().split())


def known_comuni(db, settings) -> dict:
    """Comune names this workspace already relies on, plus the provincial capitals: normalised -> written."""
    names = list(CAPITALS)
    for sql in ("SELECT DISTINCT city FROM agents WHERE city!=''", "SELECT DISTINCT city FROM benchmarks WHERE city!='' AND is_demo=0"):
        names += [r['city'] for r in db.all(sql)]
    try:
        from .omi import OmiClient
        names += [c['name'].title() for c in OmiClient(settings).cached_cities()]
    except Exception:
        pass
    return {_norm(n): n.strip() for n in names if n and n.strip()}


STREET_WORDS = {'via', 'viale', 'v.le', 'piazza', 'p.za', 'piazzale', 'corso', 'c.so', 'largo', 'vicolo', 'strada', 'alzaia',
                'ripa', 'bastioni', 'lungarno', 'lungotevere', 'contrada', 'porta'}


def _named(name: str, text: str) -> bool:
    """The name written as a place, not as part of a street ("corso Lodi", "via Padova")."""
    for match in re.finditer(r'(?<![\wÀ-ÿ])' + re.escape(name) + r'(?![\wÀ-ÿ])', text, re.I):
        before = text[:match.start()].split()
        # A place name is capitalised: "prato" or "massa" in a sentence are not Prato or Massa.
        if not match.group()[0].isupper():
            continue
        if not before or before[-1].casefold() not in STREET_WORDS:
            return True
    return False


def locate(card: Card, known: dict, context: str = '') -> None:
    """Comune (and zone) of a card that does not write "in vendita a X". Read, not guessed:
    1. the last element of its location line ("via Crema 12, Porta Romana, Milano") when it is a known comune;
       the element before it is the zone when it is a name, not a street or a number;
    2. otherwise the one known comune named by the alert subject (or the results page heading), provided the
       card names no other known comune."""
    if card.city:
        return
    line = card.address or ''
    parts = [x.strip() for x in line.split(',') if x.strip()]
    if len(parts) >= 2 and _norm(parts[-1]) in known:
        card.city = known[_norm(parts[-1])][:100]
        card.quotes['city'], card.how['city'] = line, 'località della scheda, comune noto'
        rest = parts[:-1]
        if len(rest) >= 2 and not re.search(r'\d', rest[-1]) and not STREET.match(rest[-1] + ' '):
            card.zone = rest[-1][:100]
            card.quotes['zone'], card.how['zone'] = line, 'località della scheda'
            rest = rest[:-1]
        card.address = ', '.join(rest)[:160]
        return
    named = {known[n] for n in known if _named(known[n], context)}
    if len(named) == 1:
        city = named.pop()
        if not any(_norm(name) != _norm(city) and _named(name, card.text) for name in known.values()):
            card.city = city[:100]
            card.quotes['city'], card.how['city'] = context[:160], 'oggetto dell’avviso'


def extract_cards(html: str, base_url: str | None = None, *, limit: int = 200) -> tuple[list[Card], int]:
    """Cards with a recoverable listing URL, and how many card-like blocks had none."""
    soup = BeautifulSoup(html or '', 'html.parser')
    for node in soup(['script', 'style', 'noscript', 'template', 'iframe', 'object', 'embed', 'svg', 'head', 'form']):
        node.decompose()
    link_of, anchors, portal = {}, {}, {}
    for a in soup.find_all('a', href=True):
        found = listing_link(a['href'], base_url)
        if found:
            link_of[id(a)] = found[0]
            anchors.setdefault(found[0], []).append(a)
            portal[found[0]] = found[1:]
    cards, roots = [], set()
    for url, group in list(anchors.items())[:limit]:
        key, ident = portal[url]
        root = _card_root(group[0], url, link_of, PORTALS[key]['cards'])
        roots.add(id(root))
        own = [a for a in group if a is root or root in a.parents]
        cards.append(_card(root, own or group[:1], url, key, ident))
    skipped, seen = 0, set()
    for a in soup.find_all('a'):
        if id(a) in link_of or id(a) in roots or any(id(p) in roots for p in a.parents):
            continue
        if NAV.search(_text(a)) or NAV.search(a.get('href', '')):
            continue
        block = next((p for _, p in zip(range(6), a.parents) if p.name not in ('body', 'html', '[document]') and any(_signature(p))), None)
        if block is not None and id(block) not in seen and not any(id(x) in link_of for x in block.find_all('a', href=True)):
            seen.add(id(block))
            skipped += 1
    return cards, skipped


def _listing_fields(row: dict) -> dict:
    keys = set(Listing.model_fields) - {'evidence'}
    record = {k: row[k] for k in keys if k in row}
    record['images'] = load(row.get('images'), [])
    record['is_auction'] = bool(row.get('is_auction'))
    return record


def _empty(value) -> bool:
    return value in (None, '', 'unknown', 'XXX')


def store_card(db, settings, card: Card, *, origin: str, seen_at: str | None = None, message_id: str | None = None) -> tuple[str, str]:
    """Upsert under the Capture source of the portal host: a later detail capture updates the same row.

    Returns (property id, 'created' | 'updated' | 'unchanged')."""
    from .capture import capture_source
    from .store import upsert_listing
    source = capture_source(db, PORTALS[card.portal]['host'])
    key = hashlib.sha256(card.url.encode()).hexdigest()[:24]
    old = db.one('SELECT * FROM properties WHERE source_id=? AND listing_key=? AND is_demo=0', (source['id'], key))
    timestamp = now()
    evidence = load(old['evidence'], {}) if old else {}
    record = _listing_fields(old) if old else {'listing_key': key, 'url': card.url}
    previous = evidence.get('portal_card') or {}
    # A row only known from cards takes the newest card; a row read from its detail page keeps its values
    # and takes from the card only what it lacks, plus the price: a changed price is a new observation.
    partial = old is None or bool(previous.get('incomplete'))
    method = f"{ORIGINS[origin].lower()} {PORTALS[card.portal]['name']}"
    for name in FIELDS:
        value = getattr(card, name)
        if _empty(value) or (not partial and name != 'price' and not _empty(record.get(name))):
            continue
        record[name] = value
        how = f"{method} · {card.how[name]}" if name in card.how else method
        evidence[name] = {'method': how, 'value': card.quotes.get(name, value), 'source_url': card.url}
    evidence['portal_card'] = {
        'method': method, 'value': card.text[:400], 'origin': origin, 'portal': PORTALS[card.portal]['name'],
        'seen_at': seen_at or timestamp, 'message_id': message_id, 'source_url': card.url, 'image_url': card.image,
        'price_drop': card.price_drop, 'old_price': card.old_price, 'incomplete': partial,
        'first_seen_at': previous.get('first_seen_at') or seen_at or timestamp,
    }
    listing = Listing.model_validate({**record, 'evidence': evidence})
    check = db.one('SELECT last_detail_at FROM listing_checks WHERE property_id=?', (old['id'],)) if old else None
    pid, created, changed = upsert_listing(db, settings, source['id'], listing, raw=card.text)
    # A card is not a check of the detail page: keep the freshness the detail page gave, or none.
    if check:
        db.execute('UPDATE listing_checks SET last_detail_at=? WHERE property_id=?', (check['last_detail_at'], pid))
    else:
        db.execute('DELETE FROM listing_checks WHERE property_id=?', (pid,))
    return pid, 'created' if created else 'updated' if changed else 'unchanged'


def store_cards(db, settings, cards: list[Card], *, origin: str, seen_at: str | None = None,
                message_id: str | None = None, context: str = '') -> dict:
    from .store import agent_dict, link_agent
    known = known_comuni(db, settings) if cards else {}
    summary = {'cards': len(cards), 'created': 0, 'updated': 0, 'unchanged': 0, 'no_price': 0, 'rejected': 0, 'price_drops': 0, 'property_ids': []}
    for card in cards:
        locate(card, known, context)
        try:
            pid, status = store_card(db, settings, card, origin=origin, seen_at=seen_at, message_id=message_id)
        except ValueError:
            # Schema validation of an implausible card (e.g. an out-of-range number): skipped, counted.
            summary['rejected'] += 1
            continue
        summary[status] += 1
        summary['no_price'] += card.price is None
        summary['price_drops'] += bool(card.price_drop and card.price is not None)
        summary['property_ids'].append(pid)
        if card.city:
            for row in db.all('SELECT * FROM agents WHERE active=1 AND lower(city)=lower(?)', (card.city,)):
                link_agent(db, agent_dict(row), pid)
    return summary


def complete_from_detail(db, source_id: str, listing: Listing) -> None:
    """Before a detail capture: keep what an earlier card had and the page lacks, and close 'da completare'."""
    old = db.one('SELECT * FROM properties WHERE source_id=? AND listing_key=? AND is_demo=0', (source_id, listing.listing_key))
    card = load(old['evidence'], {}).get('portal_card') if old else None
    if not card:
        return
    evidence = load(old['evidence'], {})
    if card.get('incomplete'):
        for name in FIELDS:
            if name != 'title' and _empty(getattr(listing, name)) and not _empty(old.get(name)) and name in evidence:
                setattr(listing, name, old[name])
                listing.evidence[name] = evidence[name]
    listing.evidence['portal_card'] = {**card, 'incomplete': False, 'completed_at': card.get('completed_at') or now()}


def results_page(db, settings, url: str, html: str) -> dict | None:
    """Capture of a portal results page: every card visible in the DOM the person sent, nothing more."""
    host = (urlsplit(url).hostname or '').lower()
    if not portal_key(host) or portal_for(canonical_url(url)):
        return None
    cards, skipped = extract_cards(html, url)
    if not cards:
        return None
    # The contract of a results page is written in its address (/vendita-case/, /affitto-case/).
    contract = re.search(r'/(vendita|affitto)[-/]', urlsplit(url).path)
    for card in cards:
        if contract and card.transaction_type == 'unknown':
            card.transaction_type = 'sale' if contract[1] == 'vendita' else 'rent'
            card.quotes['transaction_type'] = 'indirizzo della pagina: ' + urlsplit(url).path[:120]
    soup = BeautifulSoup(html, 'html.parser')
    heading = soup.find('h1') or soup.title
    summary = store_cards(db, settings, cards, origin='results_page', context=_text(heading)[:200] if heading else '')
    return {**summary, 'kind': 'results', 'skipped': skipped, 'portal': PORTALS[portal_key(host)]['name']}
