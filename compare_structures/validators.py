"""Input validation and environment resolution for compare-structures."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

PDB_ID_PATTERN = re.compile(r"^[0-9][A-Za-z0-9]{3}$")
SUPPORTED_STRUCTURE_SUFFIXES = frozenset({".pdb", ".cif", ".mmcif", ".ent"})


class InputValidationError(ValueError):
    """Raised for any user-input validation failure."""


def validate_input(value: str) -> dict[str, object]:
    """Classify a user-provided input string as a PDB ID or a local file.

    Returns a dict with keys: source ('pdb_id' or 'file'), id (str), path (Path or None).
    Raises InputValidationError on any problem.
    """
    if PDB_ID_PATTERN.match(value):
        return {"source": "pdb_id", "id": value.upper(), "path": None}

    # Treat as a file path if it looks file-like (contains a separator or has an extension);
    # otherwise assume the user intended a PDB ID and failed the format check.
    looks_like_path = os.sep in value or value.startswith(".") or "." in os.path.basename(value)
    if not looks_like_path:
        raise InputValidationError(
            f"not a valid PDB ID and not an existing file path: {value!r}"
        )

    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise InputValidationError(f"file not found: {value}")
    if path.suffix.lower() not in SUPPORTED_STRUCTURE_SUFFIXES:
        raise InputValidationError(
            f"unsupported format: {path.suffix} (accepted: {sorted(SUPPORTED_STRUCTURE_SUFFIXES)})"
        )
    return {"source": "file", "id": path.stem, "path": path}


def resolve_chimerax_executable() -> Path:
    """Locate the ChimeraX executable.

    Priority:
      1. CHIMERAX_PATH environment variable (must point to an existing file).
      2. `chimerax` on PATH.
    Raises InputValidationError if nothing is found.
    """
    env = os.environ.get("CHIMERAX_PATH")
    if env:
        p = Path(env)
        if not p.is_file():
            raise InputValidationError(f"CHIMERAX_PATH set but file missing: {env}")
        return p

    which = shutil.which("chimerax")
    if which:
        return Path(which)

    raise InputValidationError(
        "chimerax executable not found; set CHIMERAX_PATH or add ChimeraX to PATH"
    )
