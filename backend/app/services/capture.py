"""Vedra Capture: listings a team member opened in their own browser and sent with one click.

The person browses the portal as usual (their account, their pace). Vedra only receives the page they
chose to send: no automated navigation of the portal happens here. The page is then read like any
other: deterministic parser first, Scout for what the parser misses, then the usual enrichment.
"""
from __future__ import annotations

import secrets
from urllib.parse import urlsplit

from ..connectors.parser import canonical_url, extract_listing
from ..db import dump, load, now, uid
from ..security import token_hash
from .scout import ScoutModel, extract as scout_extract, needs_model
from .llm import ModelUnavailable
from .operations import audit
from .portal_cards import complete_from_detail, results_page
from .store import agent_dict, link_agent, upsert_listing


class CaptureRejected(ValueError):
    pass


def create_token(db, user_id: str, label: str) -> dict:
    token = 'vcap_' + secrets.token_urlsafe(32)
    ident = uid()
    db.execute('INSERT INTO capture_tokens VALUES(?,?,?,?,?,NULL)', (ident, user_id, token_hash(token), label.strip()[:80] or 'Browser', now()))
    return {'id': ident, 'token': token, 'label': label}


def user_for_token(db, token: str):
    if not token.startswith('vcap_'):
        return None
    row = db.one('''SELECT t.id token_id,u.id,u.email,u.name,u.role FROM capture_tokens t JOIN users u ON u.id=t.user_id
                    WHERE t.token_hash=?''', (token_hash(token),))
    if row:
        db.execute('UPDATE capture_tokens SET last_used_at=? WHERE id=?', (now(), row['token_id']))
    return row


def capture_source(db, host: str) -> dict:
    ident = 'capture-' + host.replace('.', '-')[:80]
    if not db.one('SELECT id FROM sources WHERE id=?', (ident,)):
        db.execute('INSERT INTO sources(id,name,kind,domain,config,permission_note,permission_at,created_at) VALUES(?,?,?,?,?,?,?,?)',
                   (ident, 'Navigazione · ' + host.removeprefix('www.'), 'import', host, dump({'capture': True}),
                    'Pagine aperte da una persona del team e inviate con Vedra Capture.', now(), now()))
    return db.one('SELECT * FROM sources WHERE id=?', (ident,))


async def capture(engine, user: dict, url: str, html: str) -> dict:
    db, settings = engine.db, engine.settings
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        raise CaptureRejected('Indirizzo della pagina non valido.')
    if not html or len(html.encode()) > settings.max_html_bytes:
        raise CaptureRejected('Pagina vuota o troppo grande.')
    # A portal results page: every card in the DOM the person sent, through the same reader as alert emails.
    results = results_page(db, settings, url, html)
    if results is not None:
        audit(db, user['id'], 'capture_results', None, {'url': url, 'cards': results['cards'], 'created': results['created']})
        return results
    url = canonical_url(url)
    source = capture_source(db, parts.hostname.lower())
    try:
        listing = extract_listing(html, url)
    except ValueError:
        listing = None
    model_used = False
    if needs_model(listing) and settings.ai_configured:
        try:
            listing = await scout_extract(ScoutModel(settings), html, url, listing)
            model_used = True
        except (ModelUnavailable, ValueError):
            if listing is None:
                raise CaptureRejected('Questa pagina non sembra la scheda di un immobile: apri l’annuncio e riprova.')
    if listing is None:
        raise CaptureRejected('Questa pagina non sembra la scheda di un immobile: apri l’annuncio e riprova.')
    await engine.availability.enrich(listing, False)
    await engine.omi.enrich(listing, listing.city or '')
    complete_from_detail(db, source['id'], listing)
    pid, created, changed = upsert_listing(db, settings, source['id'], listing, raw=dump(listing.model_dump()))
    # The page is linked to the searches of the same city, which then apply their own criteria.
    linked = 0
    if listing.city:
        for row in db.all('SELECT * FROM agents WHERE active=1 AND lower(city)=lower(?)', (listing.city,)):
            link_agent(db, agent_dict(row), pid)
            linked += 1
    audit(db, user['id'], 'capture', pid, {'url': url, 'model': model_used})
    prop = db.one('SELECT id,title,price,currency,city,zone FROM properties WHERE id=?', (pid,))
    return {'kind': 'detail', 'property_id': pid, 'created': bool(created), 'changed': bool(changed), 'title': prop['title'], 'price': prop['price'],
            'currency': prop['currency'], 'city': prop['city'], 'zone': prop['zone'], 'searches': linked, 'read_by_model': model_used}
