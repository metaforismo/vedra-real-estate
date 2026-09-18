"""Queryable strategy projections; the cited analysis remains the source of truth."""
from ..db import dump

STRATEGIES = frozenset({'value_add', 'core_plus', 'development', 'conversion'})
OBSERVED_FIELDS = (
    'title', 'price', 'surface', 'currency', 'transaction_type', 'area_basis',
    'property_type', 'condition', 'city', 'zone', 'address', 'rooms', 'bathrooms',
    'latitude', 'longitude', 'is_auction', 'description',
)


def index_strategies(con, property_id: str, analysis: dict) -> None:
    con.execute('DELETE FROM property_strategies WHERE property_id=?', (property_id,))
    values = {item.get('strategy') for item in analysis.get('strategies', []) if isinstance(item, dict)}
    for strategy in sorted(values & STRATEGIES):
        con.execute('INSERT INTO property_strategies VALUES(?,?)', (property_id, strategy))


def observation_payload(listing: dict) -> str:
    return dump({key: listing.get(key) for key in OBSERVED_FIELDS})
