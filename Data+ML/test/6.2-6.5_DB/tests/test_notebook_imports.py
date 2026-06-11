import ast
import json
from pathlib import Path


NOTEBOOK = Path(__file__).resolve().parents[1] / "database_build.ipynb"
MOVED_FUNCTIONS = {
    "get_conn",
    "dedup_restrooms",
    "dedup_parks",
    "dedup_aed",
    "dedup_healthcare",
    "dedup_ramps",
    "etl_restrooms",
    "etl_aed",
    "etl_healthcare",
    "etl_ramps",
    "apply_migrations",
    "test_weather_api",
    "etl_weather",
    "etl_venue_language",
}


def test_notebook_imports_package_without_redefining_business_functions():
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
    tree = ast.parse(code)
    defined = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert "from clearpath_db" in code
    assert not (defined & MOVED_FUNCTIONS)
