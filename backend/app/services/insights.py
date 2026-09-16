"""Explainable workspace indicators, not an appraisal or a forecast of the whole market."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median

from ..db import load

SAMPLE_LIMIT = 10000
UNKNOWN = {'', 'unknown', 'XXX', None}


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower), 2)


def asset_groups(reviews: list[dict]) -> dict[str, str]:
    parent: dict[str, str] = {}

    def find(item):
        parent.setdefault(item, item)
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    for row in reviews:
        if row['decision'] == 'same_asset':
            a, b = find(row['a']), find(row['b'])
            parent[max(a, b)] = min(a, b)
    return {item: find(item) for item in parent}


def market_groups(rows: list[dict], reviews: list[dict]) -> list[dict]:
    """Latest observation per confirmed asset, grouped by homogeneous metadata and size."""
    aliases = asset_groups(reviews)
    selected = set()
    groups = defaultdict(list)
    for p in sorted(rows, key=lambda row: (row['last_seen'], row['id']), reverse=True):
        asset = aliases.get(p['id'], p['id'])
        if asset in selected:
            continue
        selected.add(asset)
        fields = ('city', 'zone', 'property_type', 'condition', 'area_basis', 'currency', 'transaction_type')
        if any(p.get(k) in UNKNOWN for k in fields) or not p['price'] or not p['surface']:
            continue
        if p['is_auction']:
            continue
        size = '<150' if p['surface'] < 150 else '150–499' if p['surface'] < 500 else '500–1499' if p['surface'] < 1500 else '≥1500'
        key = tuple(str(p[k]).casefold() for k in fields) + (size,)
        groups[key].append(p)
    result = []
    for key, items in groups.items():
        values = [p['price'] / p['surface'] for p in items]
        sample = items[0]
        enough = len(values) >= 5
        result.append({**{k: sample[k] for k in fields}, 'size_band': key[-1], 'n': len(values),
            'median_sqm': round(median(values), 2) if enough else None,
            'p25_sqm': percentile(values, .25) if enough else None,
            'p75_sqm': percentile(values, .75) if enough else None,
            'sufficient': enough, 'latest_observed': max(p['last_seen'] for p in items)})
    return sorted(result, key=lambda item: (-item['n'], item['city'], item['zone']))[:50]


def price_changes(observations: list[dict], since: str) -> list[dict]:
    previous = {}
    reductions = {}
    for row in observations:
        pid = row['property_id']
        old = previous.get(pid)
        context = ('currency', 'transaction_type', 'area_basis', 'surface')
        compatible = old and all(row.get(k) not in UNKNOWN and row.get(k) == old.get(k) for k in context)
        if (compatible and row['observed_at'] >= since and row['price'] and old['price']
                and row['price'] < old['price']):
            reductions[pid] = {
                'property_id': pid, 'title': row['title'], 'city': row['city'],
                'previous_price': old['price'], 'price': row['price'], 'currency': row['currency'],
                'reduction_pct': round((old['price'] - row['price']) / old['price'] * 100, 1),
                'observed_at': row['observed_at'], 'source_url': row['url'],
            }
        previous[pid] = row
    return sorted(reductions.values(), key=lambda item: (-item['reduction_pct'], item['property_id']))[:20]


def workspace_insights(db, *, instant: datetime | None = None) -> dict:
    instant = instant or datetime.now(timezone.utc)
    stamp = instant.isoformat()
    cutoff7 = (instant - timedelta(days=7)).isoformat()
    cutoff30 = (instant - timedelta(days=30)).isoformat()
    cutoff90 = (instant - timedelta(days=90)).isoformat()
    aggregates = db.one('''SELECT COUNT(*) total,
        COALESCE(SUM(CASE WHEN first_seen>=? THEN 1 ELSE 0 END),0) new_7d,
        COALESCE(SUM(CASE WHEN last_seen<? THEN 1 ELSE 0 END),0) stale_7d,
        COALESCE(SUM(CASE WHEN last_seen<? THEN 1 ELSE 0 END),0) stale_30d,
        COALESCE(SUM(CASE WHEN review_status IN ('reviewing','shortlisted','due_diligence','negotiation') THEN 1 ELSE 0 END),0) in_work,
        COALESCE(SUM(CASE WHEN score>=75 THEN 1 ELSE 0 END),0) priority,
        AVG(completeness) completeness,
        COALESCE(SUM(CASE WHEN benchmark IS NOT NULL THEN 1 ELSE 0 END),0) benchmarked,
        COALESCE(SUM(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 ELSE 0 END),0) geolocated
        FROM properties WHERE is_demo=0''', (cutoff7, cutoff7, cutoff30))
    source_rows = db.all('''SELECT s.id,s.name,s.kind,s.status,s.enabled,s.last_checked,s.last_error,s.config,
        h.failures,h.next_retry,h.last_success,h.requests,
        (SELECT COUNT(*) FROM properties p WHERE p.source_id=s.id AND p.is_demo=0) listings,
        (SELECT AVG(completeness) FROM properties p WHERE p.source_id=s.id AND p.is_demo=0) completeness
        FROM sources s LEFT JOIN source_health h ON h.source_id=s.id WHERE s.kind!='demo' ORDER BY s.name''')
    sources = [{k: v for k, v in row.items() if k != 'config'} for row in source_rows if not load(row['config'], {}).get('is_demo')]
    rows = db.all('''SELECT id,title,city,zone,property_type,condition,area_basis,currency,
        transaction_type,price,surface,last_seen,is_auction FROM properties
        WHERE is_demo=0 AND last_seen>=? ORDER BY last_seen DESC,id LIMIT ?''', (cutoff90, SAMPLE_LIMIT + 1))
    total_recent = db.one('SELECT COUNT(*) n FROM properties WHERE is_demo=0 AND last_seen>=?', (cutoff90,))['n']
    truncated = len(rows) > SAMPLE_LIMIT
    rows = rows[:SAMPLE_LIMIT]
    # Context is recorded at acquisition, not backfilled from today's mutable property.
    observations = db.all('''SELECT o.property_id,o.price,o.observed_at,o.id,
        c.currency,c.transaction_type,c.area_basis,c.surface,p.title,p.city,p.url
        FROM observations o JOIN properties p ON p.id=o.property_id
        JOIN observation_context c ON c.observation_id=o.id
        WHERE p.is_demo=0 AND o.observed_at>=? ORDER BY o.observed_at DESC,o.id DESC LIMIT 20000''', (cutoff90,))
    observations.reverse()
    changes = price_changes(observations, cutoff30)
    overdue = db.all('''SELECT p.id,p.title,p.city,w.due_date,u.name owner FROM properties p
        JOIN deal_work w ON w.property_id=p.id LEFT JOIN users u ON u.id=w.owner_id
        WHERE p.is_demo=0 AND w.due_date<? AND p.review_status NOT IN ('acquired','discarded')
        ORDER BY w.due_date,p.id LIMIT 20''', (instant.date().isoformat(),))
    first_source = any(s['enabled'] for s in sources)
    actions = []
    if not first_source:
        actions.append({'kind':'setup','title':'Collega una fonte','detail':'Configura e verifica una fonte autorizzata prima di avviare le ricerche.','page':'sources'})
    if any(s['enabled'] and s['status'] in ('blocked', 'degraded') for s in sources):
        actions.append({'kind':'source','title':'Verifica le fonti bloccate','detail':'Un blocco non significa assenza di opportunità. I tentativi rispettano la pausa della fonte.','page':'sources'})
    if aggregates['stale_7d']:
        actions.append({'kind':'freshness','title':'Ricontrolla i dati meno recenti','detail':f"{aggregates['stale_7d']} annunci non riletti da oltre 7 giorni. Non sono automaticamente venduti o rimossi.",'page':'properties'})
    if aggregates['total'] > aggregates['benchmarked']:
        actions.append({'kind':'benchmark','title':'Completa i riferimenti di prezzo','detail':f"{aggregates['total'] - aggregates['benchmarked']} annunci senza benchmark compatibile. Nessuno score inventato.",'page':'market'})
    if overdue:
        actions.append({'kind':'review','title':'Revisioni da completare','detail':f'{len(overdue)} verifiche in scadenza superata, mostrate fino a 20.','page':'pipeline'})
    daily = db.all('''SELECT substr(first_seen,1,10) day,COUNT(*) total FROM properties
        WHERE is_demo=0 AND first_seen>=? GROUP BY day ORDER BY day''', (cutoff30,))
    return {'computed_at': stamp, 'archive': aggregates, 'sources': sources, 'new_by_day': daily,
            'actions': actions, 'price_reductions': changes, 'overdue': overdue,
            'segments': market_groups(rows, db.all('SELECT * FROM duplicate_reviews')),
            'sample': {'window_days':90, 'observed_listings':total_recent, 'used':len(rows),
                       'truncated':truncated, 'min_segment_size':5, 'max_observations':20000,
                       'observations_truncated':len(observations) == 20000},
            'methodology': 'Prezzi richiesti del proprio archivio negli ultimi 90 giorni. Stessa zona, tipologia, stato, superficie, valuta e operazione; aste escluse. Duplicati confermati contati una volta. Non è una stima delle compravendite o del mercato nazionale.'}
