from clearpath_db.migrations import migration_is_applied


class Cursor:
    def __init__(self, count):
        self.count = count
        self.query = None
        self.params = None

    def execute(self, query, params):
        self.query = query
        self.params = params

    def fetchone(self):
        return (self.count,)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class Connection:
    def __init__(self, count):
        self.cursor_instance = Cursor(count)

    def cursor(self):
        return self.cursor_instance


def test_column_migration_is_detected_from_information_schema():
    connection = Connection(1)
    migration = {
        "kind": "column",
        "table": "venues",
        "column": "district",
    }

    assert migration_is_applied(connection, migration)
    assert "information_schema.COLUMNS" in connection.cursor_instance.query
    assert connection.cursor_instance.params[-2:] == ("venues", "district")
