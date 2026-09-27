"""Advertisers across the archive: who handles which assets, from declared listing data only.

A shared phone or e-mail groups listings under one advertiser; a name alone groups only
identical names. Nothing here verifies a mandate: a declaration is a lead for the team.
"""
import re

from ..db import load
from .decision_facts import contact_route

CLOSED = ('sold', 'rented', 'withdrawn')


def _phone(value):
    digits = re.sub(r'[\s().-]', '', str(value or ''))
    if not re.fullmatch(r'\+?\d{6,16}', digits):
        return ''
    digits = digits.lstrip('+')
    # +39 and 0039 are the same Italian number as the national form.
    for prefix in ('0039', '39'):
        if digits.startswith(prefix) and len(digits) - len(prefix) >= 6:
            return digits[len(prefix):]
    return digits


def _email(value):
    value = str(value or '').strip().casefold()
    return value if re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', value) else ''


def _contact(row):
    evidence = load(row['evidence'], {}) or {}
    facts = evidence.get('decision_facts') if isinstance(evidence, dict) else None
    contact = facts.get('contact') if isinstance(facts, dict) else None
    return contact if isinstance(contact, dict) else {}


def directory(db, *, q='', city='', min_price=None, max_price=None, direct_only=False, limit=200):
    clauses, values = ['p.is_demo=0', "p.availability NOT IN ('sold','rented','withdrawn')"], []
    if city.strip():
        clauses.append('lower(p.city)=lower(?)'); values.append(city.strip())
    # Price bounds compare euros only: mixing currencies would rank unrelated amounts.
    for edge, sign in ((min_price, '>='), (max_price, '<=')):
        if edge is not None:
            clauses.append(f"p.currency='EUR' AND p.price{sign}?"); values.append(edge)
    rows = db.all('SELECT p.id,p.title,p.description,p.city,p.zone,p.price,p.currency,p.surface,p.url,p.evidence,p.last_seen,'
                  'p.property_type,p.review_status,s.name source_name FROM properties p JOIN sources s ON s.id=p.source_id WHERE '
                  + ' AND '.join(clauses) + ' ORDER BY p.last_seen DESC,p.id', tuple(values))
    groups, aliases, unattributed = {}, {}, 0
    for row in rows:
        contact = _contact(row)
        phone, email = _phone(contact.get('telephone')), _email(contact.get('email'))
        name = ' '.join(str(contact.get('name') or '').split())[:240]
        organization = ' '.join(str(contact.get('organization') or '').split())[:240]
        keys = [k for k in (phone and 'tel:' + phone, email and 'mail:' + email) if k]
        if not keys and (organization or name):
            keys = ['name:' + (organization or name).casefold()]
        if not keys:
            unattributed += 1
            continue
        # Phone and e-mail may each have been seen first on different listings: follow either.
        key = next((aliases[k] for k in keys if k in aliases), keys[0])
        for k in keys:
            aliases[k] = key
        route = contact_route(dict(row))
        group = groups.setdefault(key, {'id': key, 'names': {}, 'organizations': {}, 'phones': {}, 'emails': {},
                                        'listings': [], 'cities': {}, 'zones': {}, 'direct': 0, 'value_eur': 0.0,
                                        'max_price_eur': None, 'last_seen': None, 'sources': {}})
        for bucket, value in (('names', name), ('organizations', organization), ('phones', contact.get('telephone') if phone else ''),
                              ('emails', email), ('cities', row['city']), ('zones', row['zone']), ('sources', row['source_name'])):
            if value:
                group[bucket][value] = group[bucket].get(value, 0) + 1
        if route['kind'] != 'unknown':
            group['direct'] += 1
        if row['currency'] == 'EUR' and row['price']:
            group['value_eur'] += row['price']
            group['max_price_eur'] = max(group['max_price_eur'] or 0, row['price'])
        group['last_seen'] = max(filter(None, (group['last_seen'], row['last_seen'])), default=None)
        group['listings'].append({'id': row['id'], 'title': row['title'], 'city': row['city'], 'zone': row['zone'],
                                  'price': row['price'], 'currency': row['currency'], 'surface': row['surface'],
                                  'url': row['url'], 'route': route['label'] if route['kind'] != 'unknown' else None,
                                  'review_status': row['review_status']})
    top = lambda counts: sorted(counts, key=lambda k: (-counts[k], k))
    items = []
    for group in groups.values():
        item = {'id': group['id'], 'name': (top(group['names']) or [None])[0], 'organization': (top(group['organizations']) or [None])[0],
                'phone': (top(group['phones']) or [None])[0], 'email': (top(group['emails']) or [None])[0],
                'other_names': top(group['names'])[1:4], 'cities': top(group['cities']), 'zones': top(group['zones'])[:6],
                'sources': top(group['sources']), 'count': len(group['listings']), 'direct': group['direct'],
                'value_eur': round(group['value_eur']) or None, 'max_price_eur': group['max_price_eur'],
                'last_seen': group['last_seen'], 'listings': sorted(group['listings'], key=lambda x: -(x['price'] or 0))[:20]}
        if direct_only and not item['direct']:
            continue
        if q.strip():
            needle = q.strip().casefold()
            haystack = ' '.join(filter(None, [item['name'], item['organization'], item['phone'], item['email'], *item['other_names'],
                                              *item['cities'], *item['zones']])).casefold()
            if needle not in haystack:
                continue
        items.append(item)
    items.sort(key=lambda x: (-x['direct'], -x['count'], -(x['value_eur'] or 0), x['id']))
    return {'items': items[:limit], 'total': len(items), 'limited': len(items) > limit,
            'unattributed': unattributed, 'examined': len(rows)}
