"""Writer for error.json artifacts."""

from __future__ import annotations

import json
from pathlib import Path

_SCHEMA_VERSION = "1.0"
_VALID_STAGES = frozenset({"validation", "chimerax_script", "analyze_post"})
_STDERR_TAIL_CAP = 2000


def write_error(
    output_dir: Path,
    *,
    error_type: str,
    message: str,
    stage: str,
    stderr_tail: str = "",
) -> Path:
    """Write an error.json file in ``output_dir`` and return its path.

    The directory is created if missing. ``stderr_tail`` is truncated to the
    last 2000 characters to keep the artifact bounded.
    """
    if stage not in _VALID_STAGES:
        raise ValueError(f"invalid stage: {stage!r} (must be one of {sorted(_VALID_STAGES)})")

    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "error_type": error_type,
        "message": message,
        "stage": stage,
        "stderr_tail": stderr_tail[-_STDERR_TAIL_CAP:] if stderr_tail else "",
        "schema_version": _SCHEMA_VERSION,
    }
    path = output_dir / "error.json"
    path.write_text(json.dumps(payload, indent=2))
    return path
