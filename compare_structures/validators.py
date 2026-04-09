"""Input validation and environment resolution for compare-structures."""

from __future__ import annotations

import os
import platform
import re
import shutil
from pathlib import Path

PDB_ID_PATTERN = re.compile(r"^[0-9][A-Za-z0-9]{3}$")
SUPPORTED_STRUCTURE_SUFFIXES = frozenset({".pdb", ".cif", ".mmcif", ".ent"})

_CHIMERAX_VERSION_RE = re.compile(r"ChimeraX[- ]?(\d+(?:\.\d+)*)", re.IGNORECASE)

# Well-known install locations scanned when CHIMERAX_PATH is unset and
# `chimerax` is not on PATH. Each entry is (base directory, glob pattern).
# Tests monkey-patch these to point at tmp_path.
_MAC_APP_PATTERNS: tuple[tuple[Path, str], ...] = (
    (Path("/Applications"), "ChimeraX*.app"),
    (Path.home() / "Applications", "ChimeraX*.app"),
)
_LINUX_INSTALL_PATTERNS: tuple[tuple[Path, str], ...] = (
    (Path("/usr/lib"), "ucsf-chimerax*"),
    (Path("/opt/UCSF"), "ChimeraX*"),
)


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
        raise InputValidationError(f"not a valid PDB ID and not an existing file path: {value!r}")

    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise InputValidationError(f"file not found: {value}")
    if path.suffix.lower() not in SUPPORTED_STRUCTURE_SUFFIXES:
        raise InputValidationError(
            f"unsupported format: {path.suffix} (accepted: {sorted(SUPPORTED_STRUCTURE_SUFFIXES)})"
        )
    return {"source": "file", "id": path.stem, "path": path}


def _version_sort_key(path: Path) -> tuple[int, ...]:
    """Extract a numeric version tuple from a ChimeraX install path.

    Used to sort candidate installs newest-first. Unparseable paths return an
    empty tuple and therefore sort lowest. Examples::

        ChimeraX-1.11.1.app -> (1, 11, 1)
        ChimeraX-1.10.app   -> (1, 10)
        ChimeraX-1.9.app    -> (1, 9)

    Note that tuple comparison gives ``(1, 10) > (1, 9)``, which is the
    natural version order — a lexicographic string sort would get this wrong.
    """
    match = _CHIMERAX_VERSION_RE.search(str(path))
    if not match:
        return ()
    return tuple(int(n) for n in match.group(1).split(".") if n)


def _scan_filesystem_for_chimerax() -> Path | None:
    """Scan well-known install locations and return the newest ChimeraX binary.

    Supported platforms:
      - macOS (``Darwin``): scans ``/Applications`` and ``~/Applications`` for
        ``ChimeraX*.app`` bundles and returns ``<app>/Contents/bin/ChimeraX``.
      - Linux: scans ``/usr/lib`` for ``ucsf-chimerax*`` and ``/opt/UCSF``
        for ``ChimeraX*`` and returns ``<install>/bin/chimerax``.

    Returns ``None`` on other platforms or if nothing is found. Only an
    actually-existing executable file is returned, so a broken install that
    is missing its binary is skipped over to the next-newest candidate.
    """
    system = platform.system()
    if system == "Darwin":
        patterns = _MAC_APP_PATTERNS
    elif system == "Linux":
        patterns = _LINUX_INSTALL_PATTERNS
    else:
        return None

    candidates: list[Path] = []
    for base, glob in patterns:
        if not base.is_dir():
            continue
        candidates.extend(base.glob(glob))

    if not candidates:
        return None

    candidates.sort(key=_version_sort_key, reverse=True)

    for install in candidates:
        if system == "Darwin":
            bin_path = install / "Contents" / "bin" / "ChimeraX"
        else:  # Linux
            bin_path = install / "bin" / "chimerax"
        if bin_path.is_file():
            return bin_path

    return None


def resolve_chimerax_executable() -> Path:
    """Locate the ChimeraX executable.

    Priority:
      1. ``CHIMERAX_PATH`` environment variable (must point to an existing file).
      2. ``chimerax`` on ``PATH`` (looked up via ``shutil.which``; shell
         aliases do *not* count because they don't propagate to subprocesses).
      3. Well-known filesystem locations (``/Applications/ChimeraX*.app`` on
         macOS, ``/usr/lib/ucsf-chimerax*`` or ``/opt/UCSF/ChimeraX*`` on
         Linux). The newest version is selected.

    Raises :class:`InputValidationError` if nothing is found.
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

    scanned = _scan_filesystem_for_chimerax()
    if scanned is not None:
        return scanned

    raise InputValidationError(
        "chimerax executable not found; set CHIMERAX_PATH, add ChimeraX to PATH, "
        "or install ChimeraX to a standard location"
    )
