"""Guard Data-owned schema and telemetry-contract artifacts against drift."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SEED_SQL = REPO_ROOT / "docker/mysql/init/005_seed_venues.sql"
GROUPS_SQL = REPO_ROOT / "docker/mysql/init/008_healthcare_prediction_groups.sql"
MIGRATIONS = REPO_ROOT / "docker/mysql/apply_migrations.sh"
TELEMETRY_CONTRACT = REPO_ROOT / "docs/telemetry-feed-contract.md"


def test_seed_includes_representative_healthcare_venue_and_source_link():
    source = SEED_SQL.read_text()
    assert "seed-healthcare-bellevue-001" in source
    assert "'healthcare'" in source
    assert "venue-seed-002" in source


def test_prediction_group_drift_has_idempotent_schema_migration():
    source = GROUPS_SQL.read_text()
    assert "CREATE TABLE IF NOT EXISTS healthcare_prediction_groups" in source
    assert "CREATE TABLE IF NOT EXISTS healthcare_prediction_group_members" in source
    assert "uq_prediction_group_member_venue" in source
    assert "fk_prediction_group_member_group" in source


def test_existing_volume_migration_smoke_check_covers_prediction_group_tables():
    source = MIGRATIONS.read_text()
    assert "healthcare_prediction_groups" in source
    assert "healthcare_prediction_group_members" in source


def test_provider_mapping_contract_covers_runner_required_fields():
    source = TELEMETRY_CONTRACT.read_text()
    for field in ("source_venue_id", "observed_at", "load_percent", "avg_wait_minutes"):
        assert f"`{field}`" in source
    assert "venue_source_links" in source
    assert "must not invent values" in source
