"""Explicit removal of legacy demo rows. Caller must stop writers and back up first."""
from ..datasets import legacy_source
from ..db import dump, load


def plan(db):
    sources = [s['id'] for s in db.all('SELECT * FROM sources') if legacy_source(s)]
    source_ids = set(sources)
    properties = [p['id'] for p in db.all('SELECT id,source_id,is_demo FROM properties')
                  if p['is_demo'] or p['source_id'] in source_ids]
    agents = []
    mixed = []
    for agent in db.all('SELECT id,source_ids FROM agents'):
        ids = load(agent['source_ids'], [])
        if source_ids.intersection(ids):
            kept = [sid for sid in ids if sid not in source_ids]
            if kept:
                mixed.append({'id': agent['id'], 'source_ids': kept})
            else:
                agents.append(agent['id'])
    runs = [r['id'] for r in db.all('SELECT id,agent_id,is_demo FROM runs') if r['is_demo'] or r['agent_id'] in agents]
    notifications = [n['id'] for n in db.all('SELECT id,is_demo,property_id,run_id FROM notifications')
                     if n['is_demo'] or n['property_id'] in properties or n['run_id'] in runs]
    return {'sources': sources, 'properties': properties, 'agents': agents, 'runs': runs,
            'notifications': notifications, 'mixed_agents': mixed}


def remove(db):
    with db.transaction() as con:
        db.begin_write(con)
        # Use this connection throughout: the snapshot and the deletion are one transaction.
        class Snapshot:
            def all(self, sql):
                return [dict(row) for row in con.execute(sql).fetchall()]
        selected = plan(Snapshot())
        if con.execute("SELECT id FROM runs WHERE status IN ('queued','running','cancelling') LIMIT 1").fetchone():
            raise ValueError('Termina o annulla tutte le run prima della pulizia.')
        for ident in selected['notifications']:
            for table in ('mail_outbox', 'notification_reads'):
                con.execute(f'DELETE FROM {table} WHERE notification_id=?', (ident,))
            con.execute('DELETE FROM notifications WHERE id=?', (ident,))
        for ident in selected['runs']:
            for table in ('events', 'run_properties', 'semantic_tasks', 'ai_usage', 'run_capabilities'):
                con.execute(f'DELETE FROM {table} WHERE run_id=?', (ident,))
            con.execute('DELETE FROM runs WHERE id=?', (ident,))
        for ident in selected['properties']:
            con.execute('DELETE FROM observation_context WHERE observation_id IN (SELECT id FROM observations WHERE property_id=?)', (ident,))
            for table in ('agent_properties', 'run_properties', 'semantic_tasks', 'observations', 'notes',
                          'listing_checks', 'deal_work', 'scenarios', 'ai_usage'):
                con.execute(f'DELETE FROM {table} WHERE property_id=?', (ident,))
            con.execute('DELETE FROM duplicate_reviews WHERE a=? OR b=?', (ident, ident))
            con.execute('DELETE FROM properties WHERE id=?', (ident,))
        for ident in selected['agents']:
            con.execute('DELETE FROM agent_properties WHERE agent_id=?', (ident,))
            con.execute('DELETE FROM agents WHERE id=?', (ident,))
        for agent in selected['mixed_agents']:
            con.execute('UPDATE agents SET source_ids=?,active=0,next_run=NULL WHERE id=?',
                        (dump(agent['source_ids']), agent['id']))
        for ident in selected['sources']:
            for table in ('source_health', 'source_probes'):
                con.execute(f'DELETE FROM {table} WHERE source_id=?', (ident,))
            con.execute('DELETE FROM sources WHERE id=?', (ident,))
        con.execute('DELETE FROM benchmarks WHERE is_demo=1')
    return {key: len(value) for key, value in selected.items()}
