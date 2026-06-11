from pathlib import Path
import sys

# Add shared modules to path
SHARED_DIR = Path(__file__).resolve().parents[2] / 'shared'
sys.path.insert(0, str(SHARED_DIR))
