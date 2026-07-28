import subprocess
import sys


# test_package_import_has_no_database_or_network_output:
# Verifies that importing the clearpath_db package does not produce any database connections or network output.
# Uses subprocess to execute the import in an isolated process and captures stdout/stderr.
# Assertion: no output during import (no print, no connection log, no network requests).
def test_package_import_has_no_database_or_network_output():
    completed = subprocess.run(
        [sys.executable, "-c", "import clearpath_db"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == ""
    assert completed.stderr == ""
