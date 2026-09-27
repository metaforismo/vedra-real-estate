"""Append-only team contact outcomes; independent from source declarations."""
from .db import now


def upgrade(db):
    with db.transaction() as con:
        db.begin_write(con)
        if con.execute('SELECT version FROM schema_migrations WHERE version=6').fetchone():return
        con.execute('''CREATE TABLE contact_actions (
            id TEXT PRIMARY KEY, property_id TEXT NOT NULL REFERENCES properties(id),
            user_id TEXT NOT NULL REFERENCES users(id), contact_name TEXT NOT NULL,
            outcome TEXT NOT NULL, mandate_status TEXT NOT NULL, note TEXT NOT NULL,
            next_contact TEXT, created_at TEXT NOT NULL)''')
        con.execute('CREATE INDEX idx_contact_property ON contact_actions(property_id,created_at)')
        con.execute('INSERT INTO schema_migrations VALUES(6,?)',(now(),))
