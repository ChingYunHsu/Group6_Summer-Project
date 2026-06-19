import ast
import json
from pathlib import Path


NOTEBOOK = Path(__file__).resolve().parents[1] / "dqr_cleaning_pipeline.ipynb"


def _code_cells():
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    return [
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    ]


def test_notebook_is_presentation_only():
    cells = _code_cells()
    source = "\n".join(cells)
    trees = [ast.parse(cell) for cell in cells]

    assert sum(len(cell.splitlines()) for cell in cells) <= 220
    assert not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        for tree in trees
        for node in ast.walk(tree)
    )
    assert "requests." not in source
    assert ".to_csv(" not in source
    assert "SELECT " not in source.upper()
    assert "get_conn(" not in source
    assert "fetch_traffic_hourly(" not in source
    assert "detect_gps_duplicates(" not in source


def test_notebook_keeps_required_visuals_and_summaries():
    source = "\n".join(_code_cells())

    assert "EXECUTIVE SUMMARY" in source
    assert "DQ SCORE" in source
    assert "Action Items" in source
    assert "ML USABILITY" in source
    assert "dqr_dimension_scores.png" in source
    assert "dqr_missing_heatmap.png" in source
    assert "dqr_venue_scatter.png" in source
