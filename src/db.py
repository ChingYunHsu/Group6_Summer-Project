"""Shared database helper for ClearPath backend.

Provides pymysql connection factory reading from environment variables.
Used by auth, medical, and venues API modules.
"""

import os

import pymysql


def get_db_conn():
    """Create a MySQL connection using environment variables.

    Returns:
        pymysql.Connection: Active database connection.

    Raises:
        pymysql.OperationalError: If connection fails.
    """
    return pymysql.connect(
        host=os.environ.get("CLEARPATH_DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("CLEARPATH_DB_PORT", "3306")),
        user=os.environ.get("CLEARPATH_DB_USER", "clearpath_app"),
        password=os.environ.get("CLEARPATH_DB_PASSWORD", "clearpath_app"),
        database=os.environ.get("CLEARPATH_DB_NAME", "clearpath"),
        charset="utf8mb4",
        autocommit=False,
    )
