"""Tests for compare_structures.chimerax_runner (subprocess logic, mocked)."""

import subprocess
from unittest.mock import patch

import pytest

from compare_structures.chimerax_runner import (
    ChimeraxRunError,
    ChimeraxTimeoutError,
    run_chimerax_script,
)


def _fake_completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class TestRunChimeraxScript:
    def test_successful_run_returns_stdout(self, tmp_path):
        chimerax = tmp_path / "chimerax"
        chimerax.write_text("")
        script = tmp_path / "script.py"
        script.write_text("")
        with patch("subprocess.run", return_value=_fake_completed(0, "ok\n", "")):
            result = run_chimerax_script(
                chimerax_executable=chimerax,
                script_path=script,
                script_args=["--in1", "1AKE", "--in2", "4AKE"],
                timeout_seconds=60,
            )
        assert result.returncode == 0
        assert result.stdout == "ok\n"

    def test_nonzero_exit_raises(self, tmp_path):
        chimerax = tmp_path / "chimerax"
        chimerax.write_text("")
        script = tmp_path / "script.py"
        script.write_text("")
        with patch("subprocess.run", return_value=_fake_completed(1, "", "boom")):
            with pytest.raises(ChimeraxRunError) as excinfo:
                run_chimerax_script(
                    chimerax_executable=chimerax,
                    script_path=script,
                    script_args=[],
                    timeout_seconds=60,
                )
            assert "exit 1" in str(excinfo.value)
            assert excinfo.value.stderr_tail == "boom"

    def test_timeout_raises(self, tmp_path):
        chimerax = tmp_path / "chimerax"
        chimerax.write_text("")
        script = tmp_path / "script.py"
        script.write_text("")

        def _raise(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=args[0], timeout=60)

        with patch("subprocess.run", side_effect=_raise), pytest.raises(ChimeraxTimeoutError):
            run_chimerax_script(
                chimerax_executable=chimerax,
                script_path=script,
                script_args=[],
                timeout_seconds=60,
            )

    def test_command_line_structure(self, tmp_path):
        chimerax = tmp_path / "chimerax"
        chimerax.write_text("")
        script = tmp_path / "script.py"
        script.write_text("")
        captured = {}

        def _capture(cmd, **kwargs):
            captured["cmd"] = cmd
            captured["kwargs"] = kwargs
            return _fake_completed(0, "", "")

        with patch("subprocess.run", side_effect=_capture):
            run_chimerax_script(
                chimerax_executable=chimerax,
                script_path=script,
                script_args=["a", "b"],
                timeout_seconds=123,
            )
        assert captured["cmd"][0] == str(chimerax)
        assert "--nogui" in captured["cmd"]
        assert "--exit" in captured["cmd"]
        assert "--silent" in captured["cmd"]
        assert "--script" in captured["cmd"]
        script_idx = captured["cmd"].index("--script") + 1
        script_arg = captured["cmd"][script_idx]
        assert str(script) in script_arg
        assert "a" in script_arg
        assert "b" in script_arg
        assert captured["kwargs"]["timeout"] == 123


def test_chimerax_run_error_has_stderr_attr():
    e = ChimeraxRunError("x", stderr_tail="stuff")
    assert e.stderr_tail == "stuff"
