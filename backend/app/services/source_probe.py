"""Bounded source checks: one search and at most one detail, without importing records."""
import asyncio
from urllib.parse import quote

from ..connectors.parser import discover_links, extract_listing
from ..connectors.safe_http import SafeFetcher, SourceBlocked
from ..connectors.sitemap import sitemap_links
from ..db import dump, load, now
from .analysis import QUALITY_FIELDS
from .operations import source_failed, source_succeeded


async def probe(db, settings, source):
    config = load(source['config'], {})
    city = config.get('probe_city', '').strip()
    if '{city}' in config['search_url'] and not city:
        raise ValueError('Imposta il comune per il test nella configurazione della fonte.')
    health = db.one('SELECT * FROM source_health WHERE source_id=?', (source['id'],))
    if health and health['next_retry'] and health['next_retry'] > now():
        raise ValueError('Fonte in pausa dopo un errore. Riprova dopo ' + health['next_retry'])
    fetcher = SafeFetcher(source['domain'], settings)
    fetch = fetcher.browse if config.get('browser_navigation') else fetcher.rendered if config.get('render_js') else fetcher.get

    async def sample():
        html, final = await fetch(config['search_url'].replace('{city}', quote(city.lower(), safe='')))
        if config.get('discovery_mode') == 'sitemap':
            links = sitemap_links(html, final, config.get('listing_url_pattern', ''), 100)
        else:
            links, _ = discover_links(html, final, config)
        record = None
        if links:
            raw, url = await fetch(links[0])
            record = extract_listing(raw, url, config.get('fields', {})).model_dump()
        missing = [key for key in QUALITY_FIELDS if not record or record.get(key) in (None, '', 'unknown', 'XXX', [], {})]
        # Parsing a page with zero useful fields must not make a source look healthy.
        useful = bool(record and record.get('description') and (record.get('price') or record.get('surface')))
        return {'ok': useful, 'links_found': len(links), 'sample': record,
                'missing_fields': missing, 'requests': fetcher.request_count,
                'notice': 'Un annuncio verificato, nessun dato importato.' if useful else 'Nessun annuncio leggibile nel campione.'}

    try:
        result = await asyncio.wait_for(sample(), timeout=90)
        db.execute("UPDATE sources SET status=?,last_checked=?,last_error=NULL WHERE id=?",
                   ('healthy' if result['ok'] else 'unverified', now(), source['id']))
        if result['ok']:
            source_succeeded(db, source['id'])
    except Exception as exc:
        message = str(exc)[:500] if isinstance(exc, (SourceBlocked, ValueError)) else type(exc).__name__
        result = {'ok': False, 'notice': message, 'requests': fetcher.request_count}
        db.execute("UPDATE sources SET status='blocked',last_checked=?,last_error=? WHERE id=?",
                   (now(), message, source['id']))
        source_failed(db, source['id'], message, getattr(exc, 'retry_after', 0))
    db.execute('''INSERT INTO source_probes VALUES(?,?,?) ON CONFLICT(source_id)
        DO UPDATE SET checked_at=excluded.checked_at,report=excluded.report''',
        (source['id'], now(), dump(result)))
    return result
