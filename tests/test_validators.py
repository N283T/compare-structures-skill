"""Tests for compare_structures.validators."""

import pytest

from compare_structures.validators import (
    InputValidationError,
    resolve_chimerax_executable,
    validate_input,
)


class TestValidateInput:
    def test_uppercase_pdb_id(self):
        result = validate_input("1AKE")
        assert result == {"source": "pdb_id", "id": "1AKE", "path": None}

    def test_lowercase_pdb_id_normalized(self):
        result = validate_input("4ake")
        assert result == {"source": "pdb_id", "id": "4AKE", "path": None}

    def test_three_char_is_not_pdb_id_and_not_file(self, tmp_path):
        with pytest.raises(InputValidationError, match="not a valid PDB ID"):
            validate_input("1ak")

    def test_five_char_is_not_pdb_id_and_not_file(self):
        with pytest.raises(InputValidationError, match="not a valid PDB ID"):
            validate_input("12345")

    def test_existing_pdb_file(self, tmp_path):
        f = tmp_path / "structure.pdb"
        f.write_text("HEADER    TEST\n")
        result = validate_input(str(f))
        assert result["source"] == "file"
        assert result["id"] == "structure"
        assert result["path"] == f

    def test_existing_cif_file(self, tmp_path):
        f = tmp_path / "structure.cif"
        f.write_text("data_test\n")
        result = validate_input(str(f))
        assert result["source"] == "file"
        assert result["path"] == f

    def test_existing_mmcif_file(self, tmp_path):
        f = tmp_path / "structure.mmcif"
        f.write_text("data_test\n")
        result = validate_input(str(f))
        assert result["source"] == "file"

    def test_missing_file_raises(self, tmp_path):
        missing = tmp_path / "nope.pdb"
        with pytest.raises(InputValidationError, match="file not found"):
            validate_input(str(missing))

    def test_unsupported_extension_raises(self, tmp_path):
        f = tmp_path / "structure.xyz"
        f.write_text("")
        with pytest.raises(InputValidationError, match="unsupported format"):
            validate_input(str(f))


class TestResolveChimeraxExecutable:
    def test_env_var_takes_priority(self, tmp_path, monkeypatch):
        fake = tmp_path / "chimerax"
        fake.write_text("#!/bin/sh\n")
        fake.chmod(0o755)
        monkeypatch.setenv("CHIMERAX_PATH", str(fake))
        assert resolve_chimerax_executable() == fake

    def test_env_var_points_to_missing_file_raises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CHIMERAX_PATH", str(tmp_path / "nope"))
        with pytest.raises(InputValidationError, match="CHIMERAX_PATH"):
            resolve_chimerax_executable()

    def test_fallback_to_path_lookup(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CHIMERAX_PATH", raising=False)
        fake = tmp_path / "chimerax"
        fake.write_text("#!/bin/sh\n")
        fake.chmod(0o755)
        monkeypatch.setenv("PATH", str(tmp_path))
        assert resolve_chimerax_executable() == fake

    def test_no_executable_anywhere_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CHIMERAX_PATH", raising=False)
        monkeypatch.setenv("PATH", str(tmp_path))  # empty dir
        with pytest.raises(InputValidationError, match="chimerax executable not found"):
            resolve_chimerax_executable()
