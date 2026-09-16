"""Database dialects; application queries use bound qmark parameters, never interpolation."""
from __future__ import annotations

import re
import sqlite3
import hashlib
from pathlib import Path

# Preserve callers' conflict handling without making cloud dependencies mandatory locally.
IntegrityError = sqlite3.IntegrityError


def postgres_query(sql: str) -> str:
    """Translate placeholders outside literals. Percent signs must be escaped for psycopg."""
    result = []
    quoted = False
    i = 0
    while i < len(sql):
        char = sql[i]
        if char == "'":
            result.append(char)
            if quoted and i + 1 < len(sql) and sql[i + 1] == "'":
                result.append("'")
                i += 2
                continue
            quoted = not quoted
        elif char == '?' and not quoted:
            result.append('%s')
        elif char == '%':
            result.append('%%')
        else:
            result.append(char)
        i += 1
    return ''.join(result)


class SQLiteDriver:
    dialect = 'sqlite'

    def __init__(self, path: Path):
        self.path = path

    def connect(self):
        con = sqlite3.connect(self.path, timeout=15)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('PRAGMA busy_timeout=15000')
        return con

    @staticmethod
    def begin_write(con):
        con.execute('BEGIN IMMEDIATE')

    @staticmethod
    def close():
        pass


class PostgresConnection:
    def __init__(self, raw, pool, integrity_error):
        self.raw, self.pool, self.integrity_error = raw, pool, integrity_error

    def execute(self, sql: str, args=()):
        try:
            values = tuple(int(v) if isinstance(v, bool) else v for v in args)
            return self.raw.execute(postgres_query(sql), values)
        except self.integrity_error as exc:
            raise IntegrityError('Database constraint conflict') from exc

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()

    def close(self):
        self.pool.putconn(self.raw)


class PostgresDriver:
    dialect = 'postgres'

    def __init__(self, url: str, schema: str, pool_size: int):
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,47}', schema) or schema in {'public', 'auth', 'storage', 'realtime'}:
            raise ValueError('DATABASE_SCHEMA deve essere uno schema privato dedicato, per esempio vedra.')
        try:
            import psycopg
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool
        except ImportError as exc:
            raise RuntimeError('Installa requirements-cloud.txt per usare PostgreSQL/Supabase.') from exc
        self.schema = schema
        self.write_lock_key = int.from_bytes(hashlib.sha256(('vedra:write:' + schema).encode()).digest()[:8], 'big', signed=True)
        self.psycopg = psycopg

        def configure(con):
            # The role must own only this schema; no Supabase service-role key is used.
            con.execute(psycopg.sql.SQL('SET search_path TO {}, pg_catalog').format(psycopg.sql.Identifier(schema)))
            con.execute("SET statement_timeout TO '30s'")
            con.execute("SET lock_timeout TO '10s'")
            con.commit()

        self.pool = ConnectionPool(url, min_size=0, max_size=pool_size,
            timeout=15, max_idle=60, open=True, configure=configure,
            kwargs={'row_factory':dict_row, 'prepare_threshold':None, 'connect_timeout':10})

    def connect(self):
        return PostgresConnection(self.pool.getconn(), self.pool, self.psycopg.IntegrityError)

    def begin_write(self, con):
        # Serialize short compare-and-write transactions, including initially absent rows.
        con.execute('SELECT pg_advisory_xact_lock(?)', (self.write_lock_key,))

    def close(self):
        self.pool.close()
