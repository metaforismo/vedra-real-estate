"""Bounded field-by-field evidence history; missing old snapshots stay missing."""
from math import isfinite

from ..db import load
from .property_index import OBSERVED_FIELDS


def observed_price_change(previous, current):
    """Percentage between stored asking prices with unchanged measurement context."""
    if not previous or not current:return None
    if previous.get('currency') in (None,'','XXX') or previous.get('transaction_type') not in ('sale','rent'):return None
    if previous.get('area_basis') not in ('commercial','gross','net'):return None
    for key in ('price','surface'):
        for row in (previous,current):
            value=row.get(key)
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not isfinite(value) or value<=0:return None
    if any(previous.get(key)!=current.get(key) for key in ('currency','transaction_type','surface','area_basis')):return None
    change=round((current['price']/previous['price']-1)*100,1)
    return change if change and isfinite(change) else None


def observation_history(db, ident: str, before: str | None = None, limit: int = 30) -> dict:
    where, args = 'o.property_id=?', [ident]
    if before:
        pivot = db.one('SELECT observed_at,id FROM observations WHERE id=? AND property_id=?', (before, ident))
        if not pivot:
            raise ValueError('Cursore della cronologia non valido per questo immobile.')
        where += ' AND (o.observed_at<? OR (o.observed_at=? AND o.id<?))'
        args.extend([pivot['observed_at'], pivot['observed_at'], pivot['id']])
    rows = db.all('''SELECT o.id,o.observed_at,o.parser_version,v.values_json FROM observations o
        LEFT JOIN observation_values v ON v.observation_id=o.id WHERE ''' + where +
        ' ORDER BY o.observed_at DESC,o.id DESC LIMIT ?', tuple(args) + (limit+1,))
    items = []
    for index, row in enumerate(rows[:limit]):
        previous = rows[index+1] if index+1 < len(rows) else None
        current = load(row['values_json'])
        prior = load(previous['values_json']) if previous else None
        changes = []
        if current is not None and prior is not None:
            for key in OBSERVED_FIELDS:
                a, b = prior.get(key), current.get(key)
                if a != b:
                    changes.append({'field':key, 'before':a, 'after':b})
        items.append({'id':row['id'], 'observed_at':row['observed_at'], 'parser_version':row['parser_version'],
                      'baseline':previous is None, 'has_evidence':current is not None,
                      'comparable':current is not None and prior is not None,
                      'changes':changes,
                      'price_change_pct':observed_price_change(prior,current),
                      'snapshot':{key:current.get(key) for key in ('price','currency','transaction_type','availability')} if current is not None else None,
                      'previous_price_context':{k:prior.get(k) for k in ('currency','transaction_type','area_basis','surface')} if prior else None,
                      'price_context':{k:current.get(k) for k in ('currency','transaction_type','area_basis','surface')} if current else None})
    counts = db.one('''SELECT COUNT(*) total,COUNT(v.observation_id) with_fields FROM observations o
        LEFT JOIN observation_values v ON v.observation_id=o.id WHERE o.property_id=?''', (ident,))
    return {'items':items, **counts, 'next_cursor':rows[limit-1]['id'] if len(rows)>limit else None,
            'notice':'Solo campi registrati al momento della rilevazione. Le versioni precedenti alla 0.4 non vengono ricostruite dai dati attuali.'}
