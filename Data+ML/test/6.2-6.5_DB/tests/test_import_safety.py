import subprocess
import sys


def test_package_import_has_no_database_or_network_output():
    completed = subprocess.run(
        [sys.executable, "-c", "import clearpath_db"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == ""
    assert completed.stderr == ""
