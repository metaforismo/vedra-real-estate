"""Worker lifecycle shared by local mode and the dedicated VPS process."""
import asyncio
from datetime import datetime, timedelta, timezone

from ..db import now


async def serve_worker(engine, *, acquired=False):
    if not acquired:
        engine.worker_lock.acquire()
    mail = asyncio.create_task(engine.mail_loop())
    try:
        await engine.loop()
    finally:
        engine.stopping = True
        mail.cancel()
        try:
            await mail
        except asyncio.CancelledError:
            pass
        if engine.active_task and not engine.active_task.done():
            engine.active_task.cancel()
            try:
                await engine.active_task
            except asyncio.CancelledError:
                pass
        try:
            engine.db.execute('UPDATE worker_status SET stopping=1,last_tick=? WHERE instance_id=?',
                              (now(), engine.instance_id))
        finally:
            engine.worker_lock.release()


def worker_health(db, settings):
    row = db.one("SELECT * FROM worker_status WHERE id='primary'")
    recent = False
    if row and not row['stopping']:
        try:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(row['last_tick'])
            recent = timedelta(seconds=-5) <= age < timedelta(seconds=45)
        except (TypeError, ValueError):
            pass
    running = bool(db.one("SELECT id FROM runs WHERE status IN ('running','cancelling') LIMIT 1"))
    return {'healthy': recent, 'last_tick': row['last_tick'] if row else None,
            'running': running, 'stopping': bool(row and row['stopping']),
            'scheduler': settings.scheduler, 'deployment': 'embedded' if settings.worker_enabled else 'separate'}
