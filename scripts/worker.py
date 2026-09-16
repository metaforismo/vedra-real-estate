#!/usr/bin/env python3
"""Run the collector/mail scheduler separately from the HTTP API."""
import asyncio
import logging
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.config import Settings, load_env
from app.db import Database
from app.services.engine import Engine
from app.services.worker import serve_worker


async def run():
    load_env()
    settings = Settings()
    db = Database.from_settings(settings)
    try:
        db.initialize()
        engine = Engine(db, settings)
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, setattr, engine, 'stopping', True)
            except NotImplementedError:
                pass
        await serve_worker(engine)
    finally:
        db.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
