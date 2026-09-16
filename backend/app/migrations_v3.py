"""Add observation context and worker liveness without rewriting historical evidence."""
from .db import now, load
from .datasets import legacy_source

TABLES = (
    '''CREATE TABLE IF NOT EXISTS observation_context (
        observation_id TEXT PRIMARY KEY REFERENCES observations(id),
        currency TEXT NOT NULL, transaction_type TEXT NOT NULL,
        area_basis TEXT NOT NULL, surface REAL)''',
    '''CREATE TABLE IF NOT EXISTS worker_status (
        id TEXT PRIMARY KEY, instance_id TEXT NOT NULL, last_tick TEXT NOT NULL,
        started_at TEXT NOT NULL, stopping INTEGER NOT NULL DEFAULT 0)''',
    '''CREATE TABLE IF NOT EXISTS source_probes (
        source_id TEXT PRIMARY KEY REFERENCES sources(id), checked_at TEXT NOT NULL,
        report TEXT NOT NULL)''',
    'CREATE INDEX IF NOT EXISTS idx_properties_freshness ON properties(is_demo,last_seen)',
    'CREATE INDEX IF NOT EXISTS idx_observation_time ON observations(observed_at,property_id)',
)


def upgrade(db):
    with db.transaction() as con:
        db.begin_write(con)
        if con.execute('SELECT version FROM schema_migrations WHERE version=3').fetchone():
            return
        for statement in TABLES:
            con.execute(statement.replace(' REAL', ' DOUBLE PRECISION') if db.dialect=='postgres' else statement)
        legacy_ids = {row['id'] for row in con.execute('SELECT id,kind,config FROM sources').fetchall() if legacy_source(dict(row))}
        for agent in con.execute('SELECT id,source_ids FROM agents').fetchall():
            if legacy_ids.intersection(load(agent['source_ids'], [])):
                con.execute('UPDATE agents SET active=0,next_run=NULL WHERE id=?', (agent['id'],))
        # Old rows deliberately have no context. Today's attributes are not historical evidence.
        con.execute('INSERT INTO schema_migrations VALUES(3,?)', (now(),))
