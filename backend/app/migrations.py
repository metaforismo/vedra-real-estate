"""Versioned, additive migration from the 0.1 workspace. Run before starting workers."""
from .db import now

TABLES = [
    """CREATE TABLE IF NOT EXISTS listing_checks (
        property_id TEXT PRIMARY KEY REFERENCES properties(id), last_detail_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS deal_work (
        property_id TEXT PRIMARY KEY REFERENCES properties(id), owner_id TEXT REFERENCES users(id),
        due_date TEXT, checklist TEXT NOT NULL DEFAULT '{}', version INTEGER NOT NULL,
        updated_at TEXT NOT NULL, updated_by TEXT NOT NULL REFERENCES users(id))""",
    """CREATE TABLE IF NOT EXISTS scenarios (
        id TEXT PRIMARY KEY, property_id TEXT NOT NULL REFERENCES properties(id), name TEXT NOT NULL,
        inputs TEXT NOT NULL, author_id TEXT NOT NULL REFERENCES users(id), created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS duplicate_reviews (
        a TEXT NOT NULL REFERENCES properties(id), b TEXT NOT NULL REFERENCES properties(id),
        decision TEXT NOT NULL CHECK(decision IN ('same_asset','distinct')),
        user_id TEXT NOT NULL REFERENCES users(id), updated_at TEXT NOT NULL, PRIMARY KEY(a,b))""",
    """CREATE TABLE IF NOT EXISTS saved_views (
        id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), name TEXT NOT NULL,
        filters TEXT NOT NULL, created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT REFERENCES users(id), action TEXT NOT NULL,
        target_id TEXT, details TEXT NOT NULL, created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS notifications (
        id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
        property_id TEXT REFERENCES properties(id), run_id TEXT REFERENCES runs(id),
        is_demo INTEGER NOT NULL, created_at TEXT NOT NULL, dedupe_key TEXT UNIQUE NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS notification_reads (
        notification_id TEXT NOT NULL REFERENCES notifications(id), user_id TEXT NOT NULL REFERENCES users(id),
        read_at TEXT NOT NULL, PRIMARY KEY(notification_id,user_id))""",
    """CREATE TABLE IF NOT EXISTS source_health (
        source_id TEXT PRIMARY KEY REFERENCES sources(id), failures INTEGER NOT NULL DEFAULT 0,
        next_retry TEXT, last_success TEXT, last_error TEXT, requests INTEGER NOT NULL DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS mail_outbox (
        id TEXT PRIMARY KEY, notification_id TEXT NOT NULL REFERENCES notifications(id),
        recipient TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
        next_attempt TEXT NOT NULL, last_error TEXT, sent_at TEXT, UNIQUE(notification_id,recipient))""",
    """CREATE TABLE IF NOT EXISTS ai_usage (
        id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), property_id TEXT NOT NULL REFERENCES properties(id),
        model TEXT NOT NULL, input_tokens INTEGER, output_tokens INTEGER, estimated_eur REAL,
        created_at TEXT NOT NULL, usage_reported INTEGER NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS run_capabilities (
        run_id TEXT PRIMARY KEY REFERENCES runs(id), token_hash TEXT NOT NULL, expires_at TEXT NOT NULL)""",
    'CREATE INDEX IF NOT EXISTS idx_notifications_time ON notifications(is_demo,created_at)',
    'CREATE INDEX IF NOT EXISTS idx_mail_due ON mail_outbox(status,next_attempt)',
    'CREATE INDEX IF NOT EXISTS idx_ai_run ON ai_usage(run_id)',
]


def upgrade(db):
    if db.one('SELECT version FROM schema_migrations WHERE version=2'):
        return
    con = db.connect()
    try:
        # Keep referencing table names unchanged while expanding the runtime CHECK.
        con.execute('PRAGMA foreign_keys=OFF')
        con.execute('BEGIN IMMEDIATE')
        sql = con.execute("SELECT sql FROM sqlite_master WHERE name='agents'").fetchone()[0]
        if "'llm'" not in sql:
            con.execute(sql.replace('CREATE TABLE agents', 'CREATE TABLE agents_v2', 1)
                        .replace("('local','hermes')", "('local','hermes','llm')"))
            con.execute('INSERT INTO agents_v2 SELECT * FROM agents')
            con.execute('DROP TABLE agents')
            con.execute('ALTER TABLE agents_v2 RENAME TO agents')
        for statement in TABLES:
            con.execute(statement)
        if con.execute('PRAGMA foreign_key_check').fetchone():
            raise RuntimeError('Migration stopped: existing foreign key inconsistency.')
        con.execute('INSERT INTO schema_migrations VALUES(2,?)', (now(),))
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
