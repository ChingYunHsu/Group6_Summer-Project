"""Schema checks for the local-only venue seed snapshot."""

from pathlib import Path


SEED_PATH = (
    Path(__file__).resolve().parents[1]
    / "docker"
    / "mysql"
    / "init"
    / "005_seed_venues.sql"
)


def test_seed_venues_sql_is_local_testing_snapshot_only():
    ddl = SEED_PATH.read_text()
    upper = ddl.upper()

    assert "Baseline non-empty venue snapshot for local containers" in ddl
    assert "not an ETL source of truth" in ddl
    assert "local_test_snapshot" in ddl

    forbidden_statements = (
        "CREATE TABLE",
        "ALTER TABLE",
        "DROP TABLE",
        "TRUNCATE TABLE",
        "LOAD DATA",
    )
    for statement in forbidden_statements:
        assert statement not in upper


def test_seed_venues_sql_populates_core_relational_shape():
    ddl = SEED_PATH.read_text()

    assert "INSERT IGNORE INTO venues" in ddl
    assert "INSERT IGNORE INTO venue_source_links" in ddl
    assert "INSERT IGNORE INTO restroom_profiles" in ddl
    assert "INSERT IGNORE INTO healthcare_profiles" in ddl
    assert "INSERT IGNORE INTO emergency_assets" in ddl

    assert ddl.count("'local_test_snapshot'") == 5
    assert ddl.count("'seed-") >= 10
