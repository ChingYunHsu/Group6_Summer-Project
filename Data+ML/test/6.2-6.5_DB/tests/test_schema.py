from clearpath_db.schema import parse_schema_statements


def test_schema_uses_mysql_compatible_create_index_syntax():
    statements = parse_schema_statements()
    index_statements = [
        statement
        for statement in statements
        if "CREATE INDEX" in statement.upper()
    ]

    assert len(index_statements) == 2
    assert all("CREATE INDEX IF NOT EXISTS" not in statement.upper() for statement in index_statements)
    assert any("idx_venues_district" in statement for statement in index_statements)
    assert any("idx_venues_type_district" in statement for statement in index_statements)
