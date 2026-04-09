#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click>=8.1",
#     "jsonschema>=4.20",
#     "numpy>=2.0",
# ]
# ///
"""Entry point for compare-structures skill.

Invoked by SKILL.md via Bash. Delegates to compare_structures.cli.main.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from compare_structures.cli import main  # noqa: E402

if __name__ == "__main__":
    main(argv=sys.argv[1:], standalone_mode=True)
