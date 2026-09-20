from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .db_drivers import SQLiteDriver, PostgresDriver, IntegrityError
from uuid import uuid4


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def uid() -> str:
    return str(uuid4())


def dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def load(value: str | None, fallback: Any = None) -> Any:
    return json.loads(value) if value else fallback


SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS users(
 id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
 name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','analyst','viewer')), created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions(
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), csrf TEXT NOT NULL, expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources(
 id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('demo','html','import')),
 domain TEXT NOT NULL DEFAULT '', config TEXT NOT NULL DEFAULT '{}', enabled INTEGER NOT NULL DEFAULT 1,
 permission_note TEXT NOT NULL DEFAULT '', permission_at TEXT, status TEXT NOT NULL DEFAULT 'unverified',
 last_checked TEXT, last_error TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agents(
 id TEXT PRIMARY KEY, name TEXT NOT NULL, city TEXT NOT NULL, criteria TEXT NOT NULL,
 source_ids TEXT NOT NULL, runtime TEXT NOT NULL CHECK(runtime IN ('local','hermes','llm')),
 interval_minutes INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1,
 next_run TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs(
 id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agents(id), status TEXT NOT NULL,
 trigger TEXT NOT NULL, runtime TEXT NOT NULL, created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT,
 stats TEXT NOT NULL DEFAULT '{}', error TEXT, hermes_run_id TEXT, collected INTEGER NOT NULL DEFAULT 0,
 analysis_done INTEGER NOT NULL DEFAULT 0, is_demo INTEGER NOT NULL DEFAULT 0, config_snapshot TEXT NOT NULL DEFAULT '{}'
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_run_per_agent ON runs(agent_id)
 WHERE status IN ('queued','running','cancelling');
CREATE TABLE IF NOT EXISTS events(
 id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL REFERENCES runs(id),
 time TEXT NOT NULL, level TEXT NOT NULL, step TEXT NOT NULL, message TEXT NOT NULL, data TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS properties(
 id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(id), listing_key TEXT NOT NULL,
 url TEXT NOT NULL, title TEXT NOT NULL, city TEXT NOT NULL DEFAULT '', zone TEXT NOT NULL DEFAULT '',
 address TEXT, property_type TEXT NOT NULL DEFAULT 'unknown', condition TEXT NOT NULL DEFAULT 'unknown',
 price REAL, surface REAL, rooms REAL, bathrooms REAL, latitude REAL, longitude REAL,
 area_basis TEXT NOT NULL DEFAULT 'unknown', currency TEXT NOT NULL DEFAULT 'XXX',
 transaction_type TEXT NOT NULL DEFAULT 'unknown', description TEXT NOT NULL DEFAULT '',
 is_auction INTEGER NOT NULL DEFAULT 0, images TEXT NOT NULL DEFAULT '[]',
 first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, content_hash TEXT NOT NULL,
 completeness REAL NOT NULL DEFAULT 0, evidence TEXT NOT NULL DEFAULT '{}',
 analysis TEXT NOT NULL DEFAULT '{}', benchmark TEXT, score REAL, score_breakdown TEXT NOT NULL DEFAULT '[]',
 discount REAL, review_status TEXT NOT NULL DEFAULT 'new', starred INTEGER NOT NULL DEFAULT 0,
 is_demo INTEGER NOT NULL DEFAULT 0, UNIQUE(source_id,listing_key)
);
CREATE TABLE IF NOT EXISTS agent_properties(
 agent_id TEXT NOT NULL REFERENCES agents(id), property_id TEXT NOT NULL REFERENCES properties(id),
 fit INTEGER NOT NULL, fit_reasons TEXT NOT NULL DEFAULT '[]', score REAL,
 PRIMARY KEY(agent_id,property_id)
);
CREATE TABLE IF NOT EXISTS run_properties(
 run_id TEXT NOT NULL REFERENCES runs(id), property_id TEXT NOT NULL REFERENCES properties(id),
 changed INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(run_id,property_id)
);
CREATE TABLE IF NOT EXISTS semantic_tasks(
 run_id TEXT NOT NULL REFERENCES runs(id), property_id TEXT NOT NULL REFERENCES properties(id),
 content_hash TEXT NOT NULL, payload TEXT NOT NULL, submitted INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(run_id,property_id)
);
CREATE TABLE IF NOT EXISTS observations(
 id TEXT PRIMARY KEY, property_id TEXT NOT NULL REFERENCES properties(id), observed_at TEXT NOT NULL,
 price REAL, content_hash TEXT NOT NULL, snapshot_path TEXT, parser_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notes(
 id TEXT PRIMARY KEY, property_id TEXT NOT NULL REFERENCES properties(id), user_id TEXT NOT NULL REFERENCES users(id),
 body TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS benchmarks(
 id TEXT PRIMARY KEY, city TEXT NOT NULL, zone TEXT NOT NULL, property_type TEXT NOT NULL,
 condition TEXT NOT NULL, area_basis TEXT NOT NULL, currency TEXT NOT NULL DEFAULT 'EUR',
 transaction_type TEXT NOT NULL DEFAULT 'sale', min_sqm REAL NOT NULL, max_sqm REAL NOT NULL,
 period TEXT NOT NULL, source_label TEXT NOT NULL, source_url TEXT NOT NULL,
 is_demo INTEGER NOT NULL DEFAULT 0, imported_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_properties_filter ON properties(is_demo,city,score);
CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id,id);
CREATE INDEX IF NOT EXISTS idx_observations ON observations(property_id,observed_at);
CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at);
"""


class Database:
    def __init__(self, path: Path, *, url: str = '', schema: str = 'vedra', pool_size: int = 4):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.driver = PostgresDriver(url, schema, pool_size) if url else SQLiteDriver(path)
        self.dialect = self.driver.dialect

    @classmethod
    def from_settings(cls, settings):
        return cls(settings.db_path, url=settings.database_url,
                   schema=settings.database_schema, pool_size=settings.database_pool_size)

    def connect(self):
        return self.driver.connect()

    def begin_write(self, con):
        self.driver.begin_write(con)

    def close(self):
        self.driver.close()

    def healthy(self):
        if self.dialect == 'postgres':
            return self.one('SELECT 1 AS ok')['ok'] == 1
        return self.one('PRAGMA quick_check')['quick_check'] == 'ok'

    @contextmanager
    def transaction(self) -> Iterator:
        con = self.connect()
        try:
            yield con
            con.commit()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()

    def initialize(self) -> None:
        from .migrations import upgrade, upgrade_cloud
        if self.dialect == 'postgres':
            upgrade_cloud(self, SCHEMA)
        else:
            with self.transaction() as con:
                con.executescript(SCHEMA)
                con.execute('INSERT INTO schema_migrations VALUES(1,?) ON CONFLICT DO NOTHING', (now(),))
            upgrade(self)
        from .migrations_v3 import upgrade as upgrade_v3
        upgrade_v3(self)
        from .migrations_v4 import upgrade as upgrade_v4
        upgrade_v4(self)
        from .migrations_v5 import upgrade as upgrade_v5
        upgrade_v5(self)

    def all(self, sql: str, args: tuple = ()) -> list[dict]:
        with self.transaction() as con:
            return [dict(r) for r in con.execute(sql, args).fetchall()]

    def one(self, sql: str, args: tuple = ()) -> dict | None:
        rows = self.all(sql, args)
        return rows[0] if rows else None

    def execute(self, sql: str, args: tuple = ()) -> None:
        with self.transaction() as con:
            con.execute(sql, args)

    def event(self, run_id: str, step: str, message: str, level: str = "info", data: dict | None = None) -> None:
        self.execute("INSERT INTO events(run_id,time,level,step,message,data) VALUES(?,?,?,?,?,?)",
                     (run_id, now(), level, step, message, dump(data or {})))
