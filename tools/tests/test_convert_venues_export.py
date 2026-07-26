import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).parents[1] / "convert_venues_export.py"
SPEC = importlib.util.spec_from_file_location("convert_venues_export", MODULE_PATH)
converter = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(converter)


def test_converter_adds_exact_31_column_contract_without_rewriting_values(tmp_path):
    source = tmp_path / "venues_export.sql"
    destination = tmp_path / "venues_export_converted.sql"
    values = "('id-1','clinic','O\\'Brien Health', '{\\\"a\\\": 1}');"
    source.write_text("-- header\nINSERT INTO `venues` VALUES " + values, encoding="utf-8")

    converter.convert_dump(source, destination)

    converted = destination.read_text(encoding="utf-8")
    assert len(converter.VENUES_COLUMNS) == 31
    assert "INSERT INTO `venues` (`venue_id`, `venue_type`" in converted
    assert converted.endswith(values)


def test_converter_converts_each_legacy_venues_insert_chunk(tmp_path):
    source = tmp_path / "chunks.sql"
    destination = tmp_path / "out.sql"
    source.write_text("INSERT INTO venues VALUES ('a'); INSERT INTO `venues` VALUES ('b');", encoding="utf-8")
    converter.convert_dump(source, destination)
    assert destination.read_text(encoding="utf-8").count("INSERT INTO `venues` (`venue_id`") == 2


@pytest.mark.parametrize("sql", ["INSERT INTO `other` VALUES ('x');", "INSERT INTO venues (`venue_id`) VALUES ('a');"])
def test_converter_refuses_unexpected_venues_insert_shape(tmp_path, sql):
    source = tmp_path / "bad.sql"
    source.write_text(sql, encoding="utf-8")
    with pytest.raises(ValueError, match="Expected at least one"):
        converter.convert_dump(source, tmp_path / "out.sql")
