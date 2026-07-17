"""db_utils.py — Shared DB connection and query helpers for forecast-v2."""

from __future__ import annotations

import os

import pandas as pd


def get_conn():
    """Create MySQL connection (lazy pymysql import so dry-run needs no DB deps)."""
    import pymysql
    return pymysql.connect(
        host=os.environ.get("CLEARPATH_DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("CLEARPATH_DB_PORT", "3306")),
        user=os.environ.get("CLEARPATH_DB_USER", "clearpath_app"),
        password=os.environ.get("CLEARPATH_DB_PASSWORD", "clearpath_app"),
        database=os.environ.get("CLEARPATH_DB_NAME", "clearpath"),
        charset="utf8mb4",
    )


def read_sql(query: str, params: tuple | None = None) -> pd.DataFrame:
    """Execute a SQL query and return results as a DataFrame."""
    conn = get_conn()
    try:
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


def load_from_cache(context_type: str) -> dict | None:
    """Load latest non-expired payload for a given context_type from external_context_cache."""
    from json import loads as json_loads
    try:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT payload_json FROM external_context_cache "
                    "WHERE context_type=%s AND expires_at > NOW() "
                    "ORDER BY expires_at DESC LIMIT 1",
                    (context_type,),
                )
                row = cur.fetchone()
                if row:
                    payload = json_loads(row[0]) if isinstance(row[0], str) else row[0]
                    return payload
        finally:
            conn.close()
    except Exception:
        return None
    return None
