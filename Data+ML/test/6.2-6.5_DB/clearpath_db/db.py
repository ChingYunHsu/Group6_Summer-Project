import pymysql

from .config import MYSQL_CONFIG

# helper function to get a new database connection using config parameters
def get_conn():
    return pymysql.connect(**MYSQL_CONFIG)

# helper function to check if a column exists in a table, return bool
def column_exists(conn, table, column):
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s",
            (MYSQL_CONFIG["database"], table, column),
        )
        return cursor.fetchone()[0] > 0


# helper function to check if a table exists, return bool
def table_exists(conn, table):
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
            (MYSQL_CONFIG["database"], table),
        )
        return cursor.fetchone()[0] > 0

# helper function to log ETL errors with consistent format
def log_etl_error(source, record_id, error):
    print(
        f"  [{source}] record={record_id!r} failed: "
        f"{type(error).__name__}: {error}"
    )

# helper function to execute single or multiple SQL statements with error handling, return success bool
def etl_execute(conn, statements, *, source, record_id):
    if (
        isinstance(statements, tuple)
        and len(statements) == 2
        and isinstance(statements[0], str)
    ):
        statements = [statements]
    try:
        with conn.cursor() as cursor:
            # sql is string as 'INSERT INTO table (col1, col2) VALUES (%s, %s)', params is a tuple of values as (val1, val2)
            for sql, params in statements:
                cursor.execute(sql, params)
        conn.commit()
        return True
    # once catch a MySQL error, rollback and log, return False to indicate failure
    except pymysql.MySQLError as error:
        conn.rollback()
        log_etl_error(source, record_id, error)
        return False

# helper function to execute many SQL statements with error handling, return counts of successes and failures
def etl_executemany(conn, sql, params, *, source, record_id):
    try:
        with conn.cursor() as cursor:
            cursor.executemany(sql, params)
        conn.commit()
        return len(params), 0
    except pymysql.MySQLError as error:
        conn.rollback()
        log_etl_error(source, record_id, error)
        return 0, len(params)
