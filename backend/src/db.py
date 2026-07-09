"""Shared pymysql connection pool + transaction helpers.

Reused by both the auth module (src/api/auth.py) and, eventually, the
medical profile endpoints — anything that needs to talk to the real MySQL
`users`/medical tables should borrow connections from here rather than
opening its own pool.

The pool is built lazily on first use, not at import time: importing this
module must be safe in environments with no live MySQL (CI, local dev on
mock endpoints) — only actually calling get_connection()/db_cursor()/
db_transaction() touches the network.
"""

import sys
from contextlib import contextmanager

import pymysql
import pymysql.cursors

from settings import get_settings

_settings = get_settings()
_pool = None


def _get_pool() -> "PooledDB":
    global _pool
    if _pool is None:
        try:
            from dbutils.pooled_db import PooledDB
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "dbutils is required when opening a real MySQL connection. "
                "Install backend dependencies before using database-backed endpoints."
            ) from exc

        _pool = PooledDB(
            creator=pymysql,
            mincached=0,
            maxcached=_settings.db_pool_size,
            maxconnections=_settings.db_pool_size + _settings.db_max_overflow,
            blocking=True,
            ping=1,  # ping the connection before handing it out (pool_pre_ping equivalent)
            host=_settings.db_host,
            port=_settings.db_port,
            user=_settings.db_user,
            password=_settings.db_password,
            database=_settings.db_name,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )
    return _pool


def get_connection():
    """Borrow a pooled pymysql connection. Caller is responsible for closing it
    (which returns it to the pool rather than disconnecting)."""
    return _get_pool().connection()


@contextmanager
def db_cursor():
    """Yield a cursor for a single read (or one-off write) on a pooled connection."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            yield cursor
    finally:
        conn.close()


@contextmanager
def db_transaction():
    """Yield a cursor inside a transaction. Commits on success, rolls back and
    re-raises on any exception. Use for any multi-statement write."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def verify_tablespace_encryption() -> None:
    """Runtime handshake: refuse to run against a MySQL instance whose
    tablespaces for this schema are not encrypted. Hard-fails the process
    (no exception to catch — this is a deliberate fail-closed crash) so a
    misconfigured/unencrypted database can never be served silently.

    Gated by DB_ENCRYPTION_CHECK (see settings.db_encryption_check_enabled);
    callers must check that flag before invoking this in environments
    without a real, encrypted MySQL instance (e.g. CI, local dev on mocks).
    """
    try:
        with db_cursor() as cursor:
            cursor.execute(
                "SELECT NAME, ENCRYPTION FROM information_schema.INNODB_TABLESPACES "
                "WHERE NAME LIKE %s",
                (f"{_settings.db_name}/%",),
            )
            rows = cursor.fetchall()
    except pymysql.MySQLError as exc:
        sys.exit(f"FATAL: database encryption handshake failed — could not query MySQL: {exc}")

    if not rows:
        sys.exit(
            f"FATAL: database encryption handshake failed — no InnoDB tablespaces found "
            f"for schema '{_settings.db_name}'. Refusing to start against an unverifiable database."
        )

    unencrypted = [row["NAME"] for row in rows if row["ENCRYPTION"] != "Y"]
    if unencrypted:
        sys.exit(
            "FATAL: database encryption handshake failed — tablespace encryption is not "
            f"active for: {', '.join(unencrypted)}. Refusing to start against an "
            "unencrypted database."
        )
