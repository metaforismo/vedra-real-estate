"""Durable receipts for retried research configuration writes."""
from .db import now


def upgrade(db):
    with db.transaction() as con:
        db.begin_write(con)
        if con.execute('SELECT version FROM schema_migrations WHERE version=7').fetchone():return
        con.execute('''CREATE TABLE agent_write_receipts (
            request_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
            fingerprint TEXT NOT NULL, response TEXT NOT NULL, created_at TEXT NOT NULL)''')
        con.execute('INSERT INTO schema_migrations VALUES(7,?)',(now(),))
