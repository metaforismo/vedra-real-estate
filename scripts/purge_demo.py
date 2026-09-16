#!/usr/bin/env python3
"""Inspect or explicitly remove legacy demonstration rows. Never touches external sources."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--writes-stopped', action='store_true')
    parser.add_argument('--backup-confirmed', action='store_true')
    args = parser.parse_args()
    if args.apply and not (args.writes_stopped and args.backup_confirmed):
        parser.error('--apply richiede --writes-stopped e --backup-confirmed.')
    from app.config import load_env, Settings
    from app.db import Database
    from app.services.legacy_cleanup import plan, remove
    load_env()
    db = Database.from_settings(Settings())
    try:
        db.initialize()
        result = remove(db) if args.apply else {k: len(v) for k, v in plan(db).items()}
        print(json.dumps({'applied': args.apply, 'rows': result}, indent=2))
        if args.apply:
            print('Backup e snapshot storici sul disco sono conservati, non cancellati automaticamente.')
    finally:
        db.close()


if __name__ == '__main__':
    main()
