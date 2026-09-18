"""Add searchable projections and future evidence; never reconstruct past fields."""
from .db import load, now
from .services.property_index import index_strategies

TABLES = (
    '''CREATE TABLE IF NOT EXISTS property_strategies (
        property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
        strategy TEXT NOT NULL, PRIMARY KEY(property_id,strategy))''',
    '''CREATE TABLE IF NOT EXISTS observation_values (
        observation_id TEXT PRIMARY KEY REFERENCES observations(id) ON DELETE CASCADE,
        values_json TEXT NOT NULL)''',
    'CREATE INDEX IF NOT EXISTS idx_property_strategy ON property_strategies(strategy,property_id)',
    'CREATE INDEX IF NOT EXISTS idx_properties_city_type ON properties(is_demo,lower(city),lower(property_type))',
    'CREATE INDEX IF NOT EXISTS idx_deal_due ON deal_work(due_date,property_id)',
)


def upgrade(db) -> None:
    with db.transaction() as con:
        db.begin_write(con)
        if con.execute('SELECT version FROM schema_migrations WHERE version=4').fetchone():
            return
        for statement in TABLES:
            con.execute(statement)
        cursor = ''
        while True:
            rows = con.execute('SELECT id,analysis FROM properties WHERE id>? ORDER BY id LIMIT 500', (cursor,)).fetchall()
            if not rows:
                break
            for row in rows:
                index_strategies(con, row['id'], load(row['analysis'], {}))
            cursor = rows[-1]['id']
        con.execute('INSERT INTO schema_migrations VALUES(4,?)', (now(),))
