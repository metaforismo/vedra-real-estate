"""Portal alert emails: processed messages (deduplicated by Message-ID) and the mailbox check state."""
from .db import now


def upgrade(db):
    with db.transaction() as con:
        db.begin_write(con)
        if con.execute('SELECT version FROM schema_migrations WHERE version=10').fetchone():return
        # One row per message, also when ignored: the next poll neither re-reads nor re-counts it.
        con.execute('''CREATE TABLE portal_alert_messages (
            message_id TEXT PRIMARY KEY, channel TEXT NOT NULL, sender_domain TEXT NOT NULL DEFAULT '',
            portal TEXT NOT NULL DEFAULT '', subject TEXT NOT NULL DEFAULT '', sent_at TEXT, processed_at TEXT NOT NULL,
            status TEXT NOT NULL, cards INTEGER NOT NULL DEFAULT 0, created INTEGER NOT NULL DEFAULT 0,
            updated INTEGER NOT NULL DEFAULT 0, skipped INTEGER NOT NULL DEFAULT 0, note TEXT NOT NULL DEFAULT '')''')
        con.execute('CREATE INDEX idx_portal_alert_processed ON portal_alert_messages(processed_at)')
        # Mailbox position and last outcome; credentials never live here.
        con.execute('''CREATE TABLE portal_alert_state (
            id TEXT PRIMARY KEY, uid_validity TEXT, last_uid INTEGER NOT NULL DEFAULT 0,
            checked_at TEXT, ok INTEGER NOT NULL DEFAULT 0, error TEXT)''')
        con.execute('INSERT INTO schema_migrations VALUES(10,?)',(now(),))
