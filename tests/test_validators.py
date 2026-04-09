"""Tests for compare_structures.validators."""

from pathlib import Path

import pytest

from compare_structures import validators
from compare_structures.validators import (
    InputValidationError,
    _scan_filesystem_for_chimerax,
    _version_sort_key,
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
        # Also force the filesystem fallback to find nothing, otherwise on a
        # developer machine with ChimeraX installed this assertion would fail.
        monkeypatch.setattr(validators, "_scan_filesystem_for_chimerax", lambda: None)
        with pytest.raises(InputValidationError, match="chimerax executable not found"):
            resolve_chimerax_executable()

    def test_filesystem_fallback_finds_newest(self, tmp_path, monkeypatch):
        """macOS fallback: CHIMERAX_PATH unset + empty PATH + multiple installs → newest wins."""
        import platform

        # Create three fake ChimeraX installs in a fake /Applications.
        fake_apps = tmp_path / "Applications"
        fake_apps.mkdir()
        for version in ("1.9", "1.10", "1.11.1"):
            bin_dir = fake_apps / f"ChimeraX-{version}.app" / "Contents" / "bin"
            bin_dir.mkdir(parents=True)
            exe = bin_dir / "ChimeraX"
            exe.write_text("#!/bin/sh\n")
            exe.chmod(0o755)

        monkeypatch.delenv("CHIMERAX_PATH", raising=False)
        monkeypatch.setenv("PATH", str(tmp_path / "empty"))
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        monkeypatch.setattr(validators, "_MAC_APP_PATTERNS", ((fake_apps, "ChimeraX*.app"),))

        result = resolve_chimerax_executable()
        assert result == fake_apps / "ChimeraX-1.11.1.app" / "Contents" / "bin" / "ChimeraX"


class TestVersionSortKey:
    def test_dotted_versions_parsed(self):
        assert _version_sort_key(Path("ChimeraX-1.11.1.app")) == (1, 11, 1)
        assert _version_sort_key(Path("ChimeraX-1.10.app")) == (1, 10)
        assert _version_sort_key(Path("ChimeraX-1.9.app")) == (1, 9)

    def test_natural_sort_order_not_lexicographic(self):
        """The critical case: 1.10 must sort as newer than 1.9."""
        paths = [
            Path("ChimeraX-1.9.app"),
            Path("ChimeraX-1.10.app"),
            Path("ChimeraX-1.11.1.app"),
        ]
        sorted_desc = sorted(paths, key=_version_sort_key, reverse=True)
        assert sorted_desc[0] == Path("ChimeraX-1.11.1.app")
        assert sorted_desc[1] == Path("ChimeraX-1.10.app")
        assert sorted_desc[2] == Path("ChimeraX-1.9.app")

    def test_unparseable_path_returns_empty(self):
        assert _version_sort_key(Path("/something/else")) == ()


class TestScanFilesystemForChimerax:
    def test_returns_none_on_unsupported_platform(self, monkeypatch):
        import platform

        monkeypatch.setattr(platform, "system", lambda: "Windows")
        assert _scan_filesystem_for_chimerax() is None

    def test_returns_none_when_no_candidates(self, tmp_path, monkeypatch):
        import platform

        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        monkeypatch.setattr(validators, "_MAC_APP_PATTERNS", ((empty, "ChimeraX*.app"),))
        assert _scan_filesystem_for_chimerax() is None

    def test_picks_newest_version_on_darwin(self, tmp_path, monkeypatch):
        import platform

        apps = tmp_path / "Applications"
        apps.mkdir()
        for version in ("1.9", "1.10", "1.11.1"):
            bin_dir = apps / f"ChimeraX-{version}.app" / "Contents" / "bin"
            bin_dir.mkdir(parents=True)
            exe = bin_dir / "ChimeraX"
            exe.write_text("#!/bin/sh\n")
            exe.chmod(0o755)

        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        monkeypatch.setattr(validators, "_MAC_APP_PATTERNS", ((apps, "ChimeraX*.app"),))
        result = _scan_filesystem_for_chimerax()
        assert result == apps / "ChimeraX-1.11.1.app" / "Contents" / "bin" / "ChimeraX"

    def test_skips_broken_install_without_binary(self, tmp_path, monkeypatch):
        """A newer install without a binary is skipped in favor of the next-newest with one."""
        import platform

        apps = tmp_path / "Applications"
        apps.mkdir()
        # 1.11.1 missing its bin directory entirely (broken install).
        (apps / "ChimeraX-1.11.1.app" / "Contents").mkdir(parents=True)
        # 1.10 is fine.
        bin_dir = apps / "ChimeraX-1.10.app" / "Contents" / "bin"
        bin_dir.mkdir(parents=True)
        exe = bin_dir / "ChimeraX"
        exe.write_text("#!/bin/sh\n")
        exe.chmod(0o755)

        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        monkeypatch.setattr(validators, "_MAC_APP_PATTERNS", ((apps, "ChimeraX*.app"),))
        result = _scan_filesystem_for_chimerax()
        assert result == apps / "ChimeraX-1.10.app" / "Contents" / "bin" / "ChimeraX"
