#!/usr/bin/env python3
"""Copy an offline SQLite workspace into an EMPTY PostgreSQL Vedra schema.

Source is never modified. Sessions/capabilities are intentionally not transferred.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
TABLES=('users','sources','agents','runs','properties','events','agent_properties',
        'run_properties','semantic_tasks','observations','notes','benchmarks',
        'listing_checks','deal_work','scenarios','duplicate_reviews','saved_views',
        'audit_log','notifications','notification_reads','source_health','mail_outbox',
        'ai_usage','observation_context','source_probes')


def copy_rows(source, target):
    counts={}
    with target.transaction() as con:
        target.begin_write(con)
        for table in TABLES:
            if con.execute(f'SELECT COUNT(*) n FROM {table}').fetchone()['n']:
                raise ValueError('Target non vuoto: migrazione annullata senza sovrascrivere dati.')
        for table in TABLES:
            rows=source.all(f'SELECT * FROM {table}')
            counts[table]=len(rows)
            if not rows:
                continue
            columns=list(rows[0])
            query=f"INSERT INTO {table}({','.join(columns)}) VALUES({','.join('?' for _ in columns)})"
            for row in rows:
                con.execute(query,tuple(row[key] for key in columns))
        if target.dialect=='postgres':
            for table in ('events','audit_log'):
                con.execute(f"SELECT setval(pg_get_serial_sequence('{table}','id'), COALESCE(MAX(id),1), MAX(id) IS NOT NULL) FROM {table}")
    return counts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--writes-stopped',action='store_true')
    args=parser.parse_args()
    if not args.source.is_file():parser.error('File SQLite sorgente non trovato.')
    if args.apply and not args.writes_stopped:parser.error('--apply richiede --writes-stopped.')
    from app.config import load_env,Settings
    from app.db import Database
    from app.services.legacy_cleanup import remove
    load_env()
    settings=Settings()
    if args.apply and not settings.database_url:parser.error('Imposta DATABASE_URL del target PostgreSQL in .env.')
    with tempfile.TemporaryDirectory(prefix='vedra-transfer-') as folder:
        snapshot=Path(folder)/'workspace.sqlite3'
        with sqlite3.connect(args.source.resolve().as_uri()+'?mode=ro',uri=True) as original:
            with sqlite3.connect(snapshot) as backup:original.backup(backup)
        source=Database(snapshot)
        source.initialize()
        removed=remove(source)
        if not args.apply:
            print(json.dumps({'dry_run':True,'legacy_removed_in_copy':removed,
                  'rows':{table:source.one(f'SELECT COUNT(*) n FROM {table}')['n'] for table in TABLES}},indent=2))
            return
        target=Database.from_settings(settings)
        try:
            target.initialize()
            print(json.dumps({'copied':copy_rows(source,target)},indent=2))
            print('Copia anche snapshots/ nel DATA_DIR della VPS. Sessioni invalidate; sorgente invariata.')
        finally:
            target.close()


if __name__=='__main__':
    main()
