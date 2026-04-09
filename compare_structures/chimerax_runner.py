"""Subprocess orchestration for headless ChimeraX."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path


class ChimeraxRunError(RuntimeError):
    def __init__(self, message: str, *, stderr_tail: str = "") -> None:
        super().__init__(message)
        self.stderr_tail = stderr_tail


class ChimeraxTimeoutError(ChimeraxRunError):
    pass


def run_chimerax_script(
    *,
    chimerax_executable: Path,
    script_path: Path,
    script_args: list[str],
    timeout_seconds: int,
) -> subprocess.CompletedProcess:
    """Spawn ChimeraX headless to run a script with arguments.

    Uses `--nogui --exit --silent --script "<path> arg1 arg2"`. ChimeraX's --script
    takes a single shell-style string that it splits into path + argv[1:], so we
    shell-quote the script path and each argument.

    Raises ChimeraxTimeoutError on timeout and ChimeraxRunError on non-zero exit.
    """
    quoted = " ".join(shlex.quote(x) for x in [str(script_path), *script_args])
    cmd = [
        str(chimerax_executable),
        "--nogui",
        "--exit",
        "--silent",
        "--script",
        quoted,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise ChimeraxTimeoutError(
            f"chimerax subprocess timed out after {timeout_seconds}s",
            stderr_tail=(e.stderr or "")[-2000:] if hasattr(e, "stderr") else "",
        ) from e

    if result.returncode != 0:
        raise ChimeraxRunError(
            f"chimerax subprocess failed (exit {result.returncode})",
            stderr_tail=(result.stderr or "")[-2000:],
        )
    return result
