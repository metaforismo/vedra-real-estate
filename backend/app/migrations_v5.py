from .db import now,load


def upgrade(db):
    with db.transaction() as con:
        db.begin_write(con)
        if con.execute('SELECT version FROM schema_migrations WHERE version=5').fetchone():return
        con.execute("ALTER TABLE properties ADD COLUMN availability TEXT NOT NULL DEFAULT 'unknown'")
        con.execute('ALTER TABLE properties ADD COLUMN priority_score INTEGER NOT NULL DEFAULT 0')
        con.execute('CREATE INDEX idx_properties_availability ON properties(availability,priority_score)')
        from .services.availability import priority
        cursor=''
        while True:
            rows=con.execute('SELECT * FROM properties WHERE id>? ORDER BY id LIMIT 200',(cursor,)).fetchall()
            if not rows:break
            for row in rows:
                p=dict(row);p['evidence']=load(p['evidence'],{});p['analysis']=load(p['analysis'],{})
                value=priority(p,load(p['benchmark'],None))['score']
                con.execute('UPDATE properties SET priority_score=? WHERE id=?',(value,p['id']))
            cursor=rows[-1]['id']
        con.execute('INSERT INTO schema_migrations VALUES(5,?)',(now(),))
