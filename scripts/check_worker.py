#!/usr/bin/env python3
"""Exit nonzero when the shared worker heartbeat is absent or stale."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.config import Settings, load_env
from app.db import Database
from app.services.worker import worker_health

if __name__ == '__main__':
    load_env()
    settings = Settings()
    db = Database.from_settings(settings)
    try:
        result = worker_health(db, settings)
        print('Worker reachable' if result['healthy'] else 'Worker missing or stale')
        sys.exit(0 if result['healthy'] else 1)
    finally:
        db.close()
