"""Contract checks for medical profile schema/API naming."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DDL_PATH = ROOT / "docker" / "mysql" / "init" / "004_medical_profiles.sql"
ERD_PATH = ROOT / "docs" / "ERD" / "clearpath_erd.mmd"
ACTIVE_API_PATH = ROOT / "backend" / "src" / "api" / "user.py"
MEDICAL_API_PATH = ROOT / "backend" / "src" / "api" / "medical.py"
APP_PATH = ROOT / "backend" / "src" / "app.py"
COMPOSE_PATH = ROOT / "docker-compose.yml"


def test_medical_profile_migration_has_unique_004_prefix():
    init_files = sorted(path.name for path in (ROOT / "docker" / "mysql" / "init").glob("*.sql"))
    numeric_prefixes = [name.split("_", 1)[0] for name in init_files]

    assert "004_medical_profiles.sql" in init_files
    assert "002_medical_profiles.sql" not in init_files
    assert len(numeric_prefixes) == len(set(numeric_prefixes))


def test_medical_profile_names_match_between_ddl_api_and_erd():
    ddl = DDL_PATH.read_text()
    api = MEDICAL_API_PATH.read_text()
    erd = ERD_PATH.read_text()

    canonical_columns = (
        "allergies",
        "conditions",
        "medications",
        "emergency_contacts",
    )
    stale_storage_fragments = (
        "medical_conditions",
        "encrypted_payload",
        "FROM user_medical_profiles",
        "INTO user_medical_profiles",
        "UPDATE user_medical_profiles",
        "DELETE FROM user_medical_profiles",
    )

    for column in canonical_columns:
        assert column in ddl
        assert column in api
        assert column in erd

    for column in ("allergies", "medical_conditions"):
        assert re.search(rf"\b{column}\b", ddl) is None
        assert re.search(rf"\b{column}\b", erd) is None

    for fragment in stale_storage_fragments:
        assert fragment not in api


def test_medical_blueprint_is_registered_once():
    app = APP_PATH.read_text()
    user_api = ACTIVE_API_PATH.read_text()
    medical_api = MEDICAL_API_PATH.read_text()

    assert "from api.medical import bp as medical_bp" in app
    assert "app.register_blueprint(medical_bp)" in app
    assert '"/api/v1/user/medical-profile"' in medical_api
    assert '"/api/v1/user/medical-profile"' not in user_api


def test_mysql_container_loads_keyring_for_encrypted_medical_table():
    ddl = DDL_PATH.read_text()
    compose = COMPOSE_PATH.read_text()

    assert "ENCRYPTION='Y'" in ddl
    assert "--early-plugin-load=keyring_file.so" in compose
    assert "--keyring_file_data=/var/lib/mysql-keyring/keyring" in compose
    assert "clearpath_mysql_keyring:/var/lib/mysql-keyring" in compose
    assert "clearpath_mysql_keyring:" in compose
