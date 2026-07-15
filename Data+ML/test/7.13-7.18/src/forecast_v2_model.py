"""Compatibility import for the canonical top-level forecast-v2 module.

The notebook, evidence runner, and tests use ``../forecast_v2_model.py``.
This file keeps legacy Sprint 4 imports working without maintaining a second
model implementation.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_CANONICAL_PATH = Path(__file__).resolve().parents[1] / "forecast_v2_model.py"
_SPEC = importlib.util.spec_from_file_location("_forecast_v2_canonical", _CANONICAL_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover
    raise ImportError(f"Cannot load canonical forecast-v2 module: {_CANONICAL_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
for _name in dir(_MODULE):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_MODULE, _name)
