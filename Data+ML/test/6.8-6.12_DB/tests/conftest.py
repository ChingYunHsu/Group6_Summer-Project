from pathlib import Path
import sys

# Support both the new shared package and legacy direct-module imports.
TEST_ROOT = Path(__file__).resolve().parents[2]
SHARED_DIR = TEST_ROOT / 'shared'
sys.path.insert(0, str(TEST_ROOT))
sys.path.insert(0, str(SHARED_DIR))
