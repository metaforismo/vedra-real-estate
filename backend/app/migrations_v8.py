"""Allow the in-process Scout runtime alongside the existing ones."""
from .db import now

OLD = "('local','hermes','llm')"
NEW = "('local','scout','hermes','llm')"


def upgrade(db):
    if db.one('SELECT version FROM schema_migrations WHERE version=8'):
        return
    if db.dialect == 'postgres':
        with db.transaction() as con:
            db.begin_write(con)
            if con.execute('SELECT version FROM schema_migrations WHERE version=8').fetchone():
                return
            con.execute('ALTER TABLE agents DROP CONSTRAINT IF EXISTS agents_runtime_check')
            con.execute('ALTER TABLE agents ADD CONSTRAINT agents_runtime_check CHECK(runtime IN ' + NEW + ')')
            con.execute('INSERT INTO schema_migrations VALUES(8,?)', (now(),))
        return
    con = db.connect()
    try:
        # SQLite cannot alter a CHECK: rebuild the table with the same name and rows.
        con.execute('PRAGMA foreign_keys=OFF')
        con.execute('BEGIN IMMEDIATE')
        if not con.execute('SELECT version FROM schema_migrations WHERE version=8').fetchone():
            sql = con.execute("SELECT sql FROM sqlite_master WHERE name='agents'").fetchone()[0]
            if "'scout'" not in sql:
                con.execute(sql.replace('CREATE TABLE agents', 'CREATE TABLE agents_v8', 1).replace(OLD, NEW))
                con.execute('INSERT INTO agents_v8 SELECT * FROM agents')
                con.execute('DROP TABLE agents')
                con.execute('ALTER TABLE agents_v8 RENAME TO agents')
            if con.execute('PRAGMA foreign_key_check').fetchone():
                raise RuntimeError('Migration stopped: existing foreign key inconsistency.')
            con.execute('INSERT INTO schema_migrations VALUES(8,?)', (now(),))
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
