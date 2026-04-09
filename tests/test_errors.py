"""Tests for compare_structures.errors."""

import json

import pytest
from jsonschema import validate

from compare_structures.errors import write_error


def _load_error_schema():
    import pathlib
    schema_path = pathlib.Path(__file__).parent.parent / "schemas" / "error.schema.json"
    return json.loads(schema_path.read_text())


class TestWriteError:
    def test_writes_file_and_returns_path(self, tmp_path):
        path = write_error(
            output_dir=tmp_path,
            error_type="chimerax_fetch_failed",
            message="failed to fetch pdb id '9ZZZ'",
            stage="chimerax_script",
            stderr_tail="some stderr output",
        )
        assert path == tmp_path / "error.json"
        assert path.is_file()

    def test_error_json_matches_schema(self, tmp_path):
        path = write_error(
            output_dir=tmp_path,
            error_type="validation",
            message="invalid pdb id format",
            stage="validation",
            stderr_tail="",
        )
        data = json.loads(path.read_text())
        validate(data, _load_error_schema())
        assert data["error_type"] == "validation"
        assert data["stage"] == "validation"

    def test_truncates_long_stderr(self, tmp_path):
        long = "X" * 5000
        path = write_error(
            output_dir=tmp_path,
            error_type="chimerax_crash",
            message="crashed",
            stage="chimerax_script",
            stderr_tail=long,
        )
        data = json.loads(path.read_text())
        assert len(data["stderr_tail"]) == 2000
        assert data["stderr_tail"] == "X" * 2000

    def test_creates_output_dir_if_missing(self, tmp_path):
        nested = tmp_path / "missing" / "dir"
        assert not nested.exists()
        write_error(
            output_dir=nested,
            error_type="x",
            message="m",
            stage="validation",
        )
        assert (nested / "error.json").is_file()

    def test_invalid_stage_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="invalid stage"):
            write_error(
                output_dir=tmp_path,
                error_type="x",
                message="m",
                stage="not-a-stage",
            )
