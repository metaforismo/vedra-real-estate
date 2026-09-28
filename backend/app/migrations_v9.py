"""Personal tokens for the Vedra Capture browser extension."""
from .db import now


def upgrade(db):
    with db.transaction() as con:
        db.begin_write(con)
        if con.execute('SELECT version FROM schema_migrations WHERE version=9').fetchone():return
        con.execute('''CREATE TABLE capture_tokens (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), token_hash TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL, created_at TEXT NOT NULL, last_used_at TEXT)''')
        con.execute('INSERT INTO schema_migrations VALUES(9,?)',(now(),))
