# compare-structures Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code skill that compares two protein structures via ChimeraX and produces a Japanese analytical report grounded strictly in computed facts.

**Architecture:** A thin PEP 723 entry-point script (`analyze.py`) spawns headless ChimeraX to run a dedicated script (`chimerax_script.py`) that opens two structures, runs matchmaker via `chimerax.match_maker.match.cmd_match`, extracts per-residue data (Cα in the post-alignment frame via `atom.scene_coord`, SASA, SS, altloc), and writes `raw.json`. The entry point then post-processes the raw data into `facts.json` with determinis tic numpy math, and Claude turns that into `report.md` via a constrained prompt that forbids any training-data background knowledge.

**Tech Stack:** Python 3.12, `uv` with PEP 723, `numpy`, `jsonschema`, `click`, `pytest`, ChimeraX 1.9+ (Python 3.11 inside). Tests split into unit (no ChimeraX) and integration (opt-in, `@pytest.mark.chimerax`).

---

## File Structure

```
compare-structures-skill/
├── SKILL.md                              # Claude Code skill definition (Task 18)
├── analyze.py                            # PEP 723 entry point (Task 15)
├── chimerax_script.py                    # Runs inside ChimeraX (Task 13)
├── compare_structures/                   # Importable Python package
│   ├── __init__.py
│   ├── cli.py                            # click-based CLI main (Task 15)
│   ├── validators.py                     # Input validation (Task 4)
│   ├── clustering.py                     # Moved region clustering (Task 5)
│   ├── metrics.py                        # Pairing, RMSD, SASA, SS, Kabsch (Tasks 6-8)
│   ├── thresholds.py                     # Constants + drill-down logic (Task 9)
│   ├── errors.py                         # error.json writer (Task 10)
│   ├── facts_builder.py                  # Assemble facts.json (Task 11)
│   └── chimerax_runner.py                # Subprocess orchestration (Task 12)
├── templates/
│   └── report_prompt.md                  # Strict report-writing prompt (Task 17)
├── schemas/
│   ├── raw.schema.json                   # (Task 3)
│   ├── facts.schema.json                 # (Task 3)
│   └── error.schema.json                 # (Task 3)
├── tests/
│   ├── conftest.py                       # (Task 1)
│   ├── test_validators.py                # (Task 4)
│   ├── test_clustering.py                # (Task 5)
│   ├── test_metrics.py                   # (Tasks 6-8)
│   ├── test_thresholds.py                # (Task 9)
│   ├── test_errors.py                    # (Task 10)
│   ├── test_facts_builder.py             # (Task 11)
│   ├── test_chimerax_runner.py           # (Task 12)
│   ├── test_cli.py                       # (Task 15)
│   └── test_integration.py               # @pytest.mark.chimerax (Task 16)
├── docs/
│   ├── manual_review_checklist.md        # (Task 19)
│   └── superpowers/
│       ├── specs/2026-04-09-compare-structures-design.md   # already committed
│       └── plans/2026-04-09-compare-structures-implementation.md  # this file
├── pyproject.toml                        # Dev tooling only (Task 1)
├── README.md                             # (Task 20)
└── .gitignore                            # already committed
```

**Design notes:**

- `analyze.py` is a PEP 723 script at the top level. It inserts its sibling directory into `sys.path` so it can `import compare_structures.cli`. The package modules import `numpy`, `jsonschema`, `click` which come from the PEP 723 dependency declaration.
- `chimerax_script.py` is NOT a PEP 723 script — it runs inside ChimeraX's own Python 3.11 interpreter where numpy is already available. It is invoked by `chimerax_runner.py` as a subprocess argument to `chimerax --nogui --exit --script`.
- `compare_structures/` is a plain Python package (no installation). Tests import it by adding the repo root to `sys.path` via `conftest.py`.
- `runs/` (gitignored) is where per-run artifacts land — one sub-directory per analysis.

---

## Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `compare_structures/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/__init__.py`
- Modify: `.gitignore` (already contains needed entries — verify only)

- [ ] **Step 1: Create the package directory structure**

Run:
```bash
cd /Users/nagaet/explain-conf-skill
mkdir -p compare_structures tests templates schemas docs
```

Expected: four new directories created, no errors.

- [ ] **Step 2: Write `pyproject.toml` (dev tooling only, no package install)**

Create `pyproject.toml`:
```toml
[project]
name = "compare-structures-skill"
version = "0.0.1"
description = "Claude Code skill comparing two protein structures via ChimeraX"
requires-python = ">=3.12"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "numpy>=2.0",
    "jsonschema>=4.20",
    "click>=8.1",
    "ruff>=0.4",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "chimerax: integration tests that require a ChimeraX installation (opt-in)",
]
addopts = "-ra --strict-markers"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM", "C4"]
```

- [ ] **Step 3: Create `compare_structures/__init__.py`**

Create `compare_structures/__init__.py`:
```python
"""compare-structures skill internal package."""

__version__ = "0.0.1"
```

- [ ] **Step 4: Create `tests/__init__.py` and `tests/conftest.py`**

Create `tests/__init__.py`:
```python
```
(empty file)

Create `tests/conftest.py`:
```python
"""pytest configuration — adds repo root to sys.path so tests can import compare_structures."""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
```

- [ ] **Step 5: Verify pytest can discover and run zero tests**

Run: `uv run --with pytest pytest -q`
Expected: `no tests ran in 0.XXs` (exit 0, no collection errors).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml compare_structures/__init__.py tests/__init__.py tests/conftest.py
git commit -m "chore: scaffold project layout and pytest config"
```

---

## Task 2: JSON Schemas

**Files:**
- Create: `schemas/raw.schema.json`
- Create: `schemas/facts.schema.json`
- Create: `schemas/error.schema.json`

No tests in this task — schemas are exercised by later tests.

- [ ] **Step 1: Write `schemas/raw.schema.json`**

Create `schemas/raw.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "compare-structures raw.json",
  "type": "object",
  "required": ["input1", "input2", "matchmaker", "chains", "schema_version"],
  "properties": {
    "input1": {"$ref": "#/$defs/input"},
    "input2": {"$ref": "#/$defs/input"},
    "matchmaker": {
      "type": "object",
      "required": ["reference_model", "moved_model", "full_rmsd", "final_rmsd", "n_full_pairs", "n_final_pairs"],
      "properties": {
        "reference_model": {"type": "integer"},
        "moved_model": {"type": "integer"},
        "full_rmsd": {"type": "number"},
        "final_rmsd": {"type": "number"},
        "n_full_pairs": {"type": "integer"},
        "n_final_pairs": {"type": "integer"},
        "per_chain": {"type": "array"}
      }
    },
    "chains": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["chain_id", "model", "residues"],
        "properties": {
          "chain_id": {"type": "string"},
          "model": {"type": "integer"},
          "residues": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["res_num", "res_name", "ca_coord", "sasa", "ss_type"],
              "properties": {
                "res_num": {"type": "integer"},
                "res_name": {"type": "string"},
                "ca_coord": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                "sasa": {"type": "number"},
                "ss_type": {"type": "string", "enum": ["H", "E", "C"]},
                "altloc_ids": {"type": "array", "items": {"type": "string"}},
                "max_occupancy": {"type": "number"}
              }
            }
          }
        }
      }
    },
    "chimerax_version": {"type": "string"},
    "schema_version": {"type": "string"}
  },
  "$defs": {
    "input": {
      "type": "object",
      "required": ["id", "source", "model_id"],
      "properties": {
        "id": {"type": "string"},
        "source": {"type": "string", "enum": ["pdb_id", "file"]},
        "model_id": {"type": "integer"}
      }
    }
  }
}
```

- [ ] **Step 2: Write `schemas/facts.schema.json`**

Create `schemas/facts.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "compare-structures facts.json",
  "type": "object",
  "required": ["inputs", "alignment", "chain_summary", "moved_regions", "drill_down_flags", "artifacts", "meta"],
  "properties": {
    "inputs": {
      "type": "object",
      "required": ["structure_1", "structure_2"],
      "properties": {
        "structure_1": {"type": "object"},
        "structure_2": {"type": "object"}
      }
    },
    "alignment": {
      "type": "object",
      "required": ["method", "overall_rmsd_angstrom", "n_aligned_residues", "sequence_identity"],
      "properties": {
        "method": {"type": "string"},
        "reference": {"type": ["string", "null"]},
        "moved": {"type": ["string", "null"]},
        "overall_rmsd_angstrom": {"type": "number"},
        "refined_rmsd_angstrom": {"type": "number"},
        "n_aligned_residues": {"type": "integer"},
        "sequence_identity": {"type": "number"}
      }
    },
    "chain_summary": {"type": "array"},
    "moved_regions": {"type": "array"},
    "top_ca_movers": {"type": "array"},
    "sasa_changes": {"type": "object"},
    "ss_changes": {"type": "array"},
    "altloc_residues": {
      "type": "object",
      "properties": {
        "structure_1": {"type": "array"},
        "structure_2": {"type": "array"}
      }
    },
    "drill_down_flags": {
      "type": "object",
      "required": ["report_residue_level", "report_sasa", "report_ss_changes"],
      "properties": {
        "report_residue_level": {"type": "boolean"},
        "report_sasa": {"type": "boolean"},
        "report_ss_changes": {"type": "boolean"},
        "reasons": {"type": "object"}
      }
    },
    "warnings": {"type": "array", "items": {"type": "string"}},
    "condition": {"type": ["string", "null"]},
    "artifacts": {
      "type": "object",
      "required": ["aligned_structure"],
      "properties": {
        "aligned_structure": {"type": "string"}
      }
    },
    "meta": {
      "type": "object",
      "required": ["schema_version", "generated_at"],
      "properties": {
        "schema_version": {"type": "string"},
        "chimerax_version": {"type": "string"},
        "generated_at": {"type": "string"}
      }
    }
  }
}
```

- [ ] **Step 3: Write `schemas/error.schema.json`**

Create `schemas/error.schema.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "compare-structures error.json",
  "type": "object",
  "required": ["error_type", "message", "stage", "schema_version"],
  "properties": {
    "error_type": {"type": "string"},
    "message": {"type": "string"},
    "stage": {"type": "string", "enum": ["validation", "chimerax_script", "analyze_post"]},
    "stderr_tail": {"type": "string"},
    "schema_version": {"type": "string"}
  }
}
```

- [ ] **Step 4: Verify schemas parse as valid JSON Schemas**

Run:
```bash
uv run --with jsonschema python -c "
import json, pathlib
from jsonschema import Draft202012Validator
for p in pathlib.Path('schemas').glob('*.json'):
    schema = json.loads(p.read_text())
    Draft202012Validator.check_schema(schema)
    print(f'ok: {p.name}')
"
```

Expected:
```
ok: raw.schema.json
ok: facts.schema.json
ok: error.schema.json
```

- [ ] **Step 5: Commit**

```bash
git add schemas/
git commit -m "chore: add JSON schemas for raw/facts/error artifacts"
```

---

## Task 3: `compare_structures/validators.py` — input validation

**Files:**
- Create: `compare_structures/validators.py`
- Create: `tests/test_validators.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_validators.py`:
```python
"""Tests for compare_structures.validators."""

import os
from pathlib import Path

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
```

- [ ] **Step 2: Run the failing tests**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_validators.py -v`
Expected: collection error — module `compare_structures.validators` does not exist.

- [ ] **Step 3: Implement `compare_structures/validators.py`**

Create `compare_structures/validators.py`:
```python
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
```

- [ ] **Step 4: Run the tests until green**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_validators.py -v`
Expected: all 14 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add compare_structures/validators.py tests/test_validators.py
git commit -m "feat: add input validators for PDB IDs, files, and ChimeraX executable"
```

---

## Task 4: `compare_structures/clustering.py` — moved-region clustering

**Files:**
- Create: `compare_structures/clustering.py`
- Create: `tests/test_clustering.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_clustering.py`:
```python
"""Tests for compare_structures.clustering."""

import numpy as np

from compare_structures.clustering import MovedRegion, cluster_moved_regions


class TestClusterMovedRegions:
    def test_single_contiguous_region(self):
        residues = [10, 11, 12, 13, 14, 15]
        disps = np.array([0.1, 4.0, 5.0, 4.5, 3.5, 0.2])
        regions = cluster_moved_regions("A", residues, disps,
                                        min_displacement=3.0, min_length=3, gap_tolerance=3)
        assert len(regions) == 1
        r = regions[0]
        assert r.chain_id == "A"
        assert r.residue_range == (11, 14)
        assert r.n_residues == 4
        assert r.max_displacement == 5.0

    def test_two_distinct_regions_no_merge(self):
        residues = list(range(1, 21))
        disps = np.zeros(20)
        disps[2:6] = 4.0   # residues 3-6 (indices 2-5)
        disps[12:16] = 4.5 # residues 13-16 (indices 12-15)
        regions = cluster_moved_regions("A", residues, disps,
                                        min_displacement=3.0, min_length=3, gap_tolerance=3)
        assert len(regions) == 2
        assert regions[0].residue_range == (3, 6)
        assert regions[1].residue_range == (13, 16)

    def test_merge_across_small_gap(self):
        residues = list(range(1, 21))
        disps = np.zeros(20)
        disps[2:6] = 4.0   # residues 3-6
        disps[8:12] = 4.0  # residues 9-12
        # gap between end (6) and start (9) is residues 7,8 => 2 residues, <= gap_tolerance=3
        regions = cluster_moved_regions("A", residues, disps,
                                        min_displacement=3.0, min_length=3, gap_tolerance=3)
        assert len(regions) == 1
        assert regions[0].residue_range == (3, 12)

    def test_gap_too_large_keeps_regions_split(self):
        residues = list(range(1, 21))
        disps = np.zeros(20)
        disps[2:6] = 4.0
        disps[12:16] = 4.0
        # gap is residues 7..12 => 5 residues, > gap_tolerance=3
        regions = cluster_moved_regions("A", residues, disps,
                                        min_displacement=3.0, min_length=3, gap_tolerance=3)
        assert len(regions) == 2

    def test_below_min_length_dropped(self):
        residues = list(range(1, 11))
        disps = np.zeros(10)
        disps[3:5] = 4.0  # only 2 residues — below min_length=3
        regions = cluster_moved_regions("A", residues, disps,
                                        min_displacement=3.0, min_length=3, gap_tolerance=3)
        assert regions == []

    def test_all_below_threshold_returns_empty(self):
        residues = list(range(1, 11))
        disps = np.full(10, 1.0)
        regions = cluster_moved_regions("A", residues, disps,
                                        min_displacement=3.0, min_length=3, gap_tolerance=3)
        assert regions == []

    def test_length_mismatch_raises(self):
        import pytest
        with pytest.raises(ValueError, match="length mismatch"):
            cluster_moved_regions("A", [1, 2, 3], np.array([1.0, 2.0]),
                                  min_displacement=3.0, min_length=3, gap_tolerance=3)

    def test_moved_region_statistics(self):
        residues = [10, 11, 12, 13, 14]
        disps = np.array([4.0, 5.0, 6.0, 5.0, 4.0])
        regions = cluster_moved_regions("B", residues, disps,
                                        min_displacement=3.0, min_length=3, gap_tolerance=3)
        assert len(regions) == 1
        r = regions[0]
        assert r.chain_id == "B"
        assert r.residue_range == (10, 14)
        assert r.n_residues == 5
        assert abs(r.mean_displacement - 4.8) < 1e-9
        assert r.max_displacement == 6.0
```

- [ ] **Step 2: Run the failing tests**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_clustering.py -v`
Expected: ImportError — module not found.

- [ ] **Step 3: Implement `compare_structures/clustering.py`**

Create `compare_structures/clustering.py`:
```python
"""Cluster residues with high Cα displacement into contiguous moved regions."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MovedRegion:
    chain_id: str
    residue_range: tuple[int, int]  # inclusive [start, end] in residue numbers
    n_residues: int
    mean_displacement: float
    max_displacement: float


def cluster_moved_regions(
    chain_id: str,
    residues: list[int],
    displacements: np.ndarray,
    *,
    min_displacement: float,
    min_length: int,
    gap_tolerance: int,
) -> list[MovedRegion]:
    """Cluster contiguous high-displacement residues into moved regions.

    Parameters
    ----------
    chain_id : str
        Chain identifier stored on every returned region.
    residues : list[int]
        Residue numbers, in ascending order. May contain gaps (missing residues).
    displacements : np.ndarray
        Per-residue Cα displacement in Å, same length as ``residues``.
    min_displacement : float
        A residue is "high" if its displacement strictly exceeds this threshold.
    min_length : int
        Final regions with fewer than this many residues are dropped.
    gap_tolerance : int
        Two high-runs separated by at most this many low residues (by residue number,
        not index) are merged into a single region.
    """
    if len(residues) != len(displacements):
        raise ValueError(
            f"residues and displacements length mismatch: "
            f"{len(residues)} vs {len(displacements)}"
        )
    if len(residues) == 0:
        return []

    high = displacements > min_displacement

    # Contiguous runs of high residues by index.
    runs: list[tuple[int, int]] = []
    i = 0
    n = len(high)
    while i < n:
        if not high[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and high[j + 1]:
            j += 1
        runs.append((i, j))
        i = j + 1

    # Merge runs whose residue-number gap is within tolerance.
    merged: list[tuple[int, int]] = []
    for start, end in runs:
        if merged:
            prev_end = merged[-1][1]
            residue_gap = residues[start] - residues[prev_end] - 1
            if residue_gap <= gap_tolerance:
                merged[-1] = (merged[-1][0], end)
                continue
        merged.append((start, end))

    # Build MovedRegion objects, filtering by length.
    result: list[MovedRegion] = []
    for start, end in merged:
        n_res = end - start + 1
        if n_res < min_length:
            continue
        slice_ = displacements[start : end + 1]
        result.append(
            MovedRegion(
                chain_id=chain_id,
                residue_range=(int(residues[start]), int(residues[end])),
                n_residues=n_res,
                mean_displacement=float(slice_.mean()),
                max_displacement=float(slice_.max()),
            )
        )
    return result
```

- [ ] **Step 4: Run the tests until green**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_clustering.py -v`
Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add compare_structures/clustering.py tests/test_clustering.py
git commit -m "feat: add moved-region clustering with gap merge and length filter"
```

---

## Task 5: `compare_structures/metrics.py` — residue pairing, RMSD, displacement, sequence identity

**Files:**
- Create: `compare_structures/metrics.py` (first half — pairing, displacement, RMSD, sequence_identity)
- Create: `tests/test_metrics.py` (first half)

- [ ] **Step 1: Write failing tests**

Create `tests/test_metrics.py`:
```python
"""Tests for compare_structures.metrics."""

import numpy as np
import pytest

from compare_structures.metrics import (
    PairedResidue,
    displacement,
    kabsch_transform,
    pair_residues,
    rmsd,
    rotation_angle_deg,
    sasa_deltas,
    sequence_identity,
    ss_changes,
)


def _make_residue(res_num, res_name, ca, sasa=0.0, ss="C", altloc=None):
    return {
        "chain_id": "A",
        "res_num": res_num,
        "res_name": res_name,
        "ca_coord": list(ca),
        "sasa": sasa,
        "ss_type": ss,
        "altloc_ids": altloc or [],
        "max_occupancy": 1.0,
    }


class TestPairResidues:
    def test_perfect_pairing(self):
        c1 = [_make_residue(1, "MET", (0, 0, 0)), _make_residue(2, "ALA", (1, 0, 0))]
        c2 = [_make_residue(1, "MET", (0, 1, 0)), _make_residue(2, "ALA", (1, 1, 0))]
        paired = pair_residues(c1, c2)
        assert len(paired) == 2
        assert paired[0].res_num == 1
        assert paired[0].res_name_1 == "MET"
        assert paired[0].res_name_2 == "MET"

    def test_ordered_by_residue_number(self):
        c1 = [_make_residue(5, "MET", (0, 0, 0)), _make_residue(2, "ALA", (1, 0, 0))]
        c2 = [_make_residue(2, "ALA", (1, 1, 0)), _make_residue(5, "MET", (0, 1, 0))]
        paired = pair_residues(c1, c2)
        assert [p.res_num for p in paired] == [2, 5]

    def test_unmatched_residues_dropped(self):
        c1 = [_make_residue(1, "MET", (0, 0, 0)), _make_residue(2, "ALA", (1, 0, 0))]
        c2 = [_make_residue(2, "ALA", (1, 0, 0))]
        paired = pair_residues(c1, c2)
        assert [p.res_num for p in paired] == [2]

    def test_mutation_still_pairs(self):
        c1 = [_make_residue(10, "LEU", (0, 0, 0))]
        c2 = [_make_residue(10, "VAL", (0, 0, 0))]
        paired = pair_residues(c1, c2)
        assert len(paired) == 1
        assert paired[0].res_name_1 == "LEU"
        assert paired[0].res_name_2 == "VAL"


class TestDisplacement:
    def test_zero_displacement(self):
        c1 = [_make_residue(1, "MET", (0, 0, 0))]
        c2 = [_make_residue(1, "MET", (0, 0, 0))]
        paired = pair_residues(c1, c2)
        d = displacement(paired)
        assert d.shape == (1,)
        assert d[0] == 0.0

    def test_unit_displacement(self):
        c1 = [_make_residue(1, "MET", (0, 0, 0))]
        c2 = [_make_residue(1, "MET", (1, 0, 0))]
        paired = pair_residues(c1, c2)
        d = displacement(paired)
        assert abs(d[0] - 1.0) < 1e-12

    def test_3_4_5_triangle(self):
        c1 = [_make_residue(1, "MET", (0, 0, 0))]
        c2 = [_make_residue(1, "MET", (3, 4, 0))]
        paired = pair_residues(c1, c2)
        d = displacement(paired)
        assert abs(d[0] - 5.0) < 1e-12


class TestRMSD:
    def test_empty(self):
        assert rmsd([]) == 0.0

    def test_known_value(self):
        # Three residues with displacements 1, 2, 3
        # RMSD = sqrt((1+4+9)/3) = sqrt(14/3) ~= 2.16025
        c1 = [
            _make_residue(1, "A", (0, 0, 0)),
            _make_residue(2, "A", (0, 0, 0)),
            _make_residue(3, "A", (0, 0, 0)),
        ]
        c2 = [
            _make_residue(1, "A", (1, 0, 0)),
            _make_residue(2, "A", (2, 0, 0)),
            _make_residue(3, "A", (3, 0, 0)),
        ]
        paired = pair_residues(c1, c2)
        assert abs(rmsd(paired) - np.sqrt(14 / 3)) < 1e-12


class TestSequenceIdentity:
    def test_all_identical(self):
        c1 = [_make_residue(1, "MET", (0, 0, 0)), _make_residue(2, "ALA", (0, 0, 0))]
        c2 = [_make_residue(1, "MET", (0, 0, 0)), _make_residue(2, "ALA", (0, 0, 0))]
        paired = pair_residues(c1, c2)
        assert sequence_identity(paired) == 1.0

    def test_half_mutated(self):
        c1 = [_make_residue(1, "MET", (0, 0, 0)), _make_residue(2, "ALA", (0, 0, 0))]
        c2 = [_make_residue(1, "MET", (0, 0, 0)), _make_residue(2, "VAL", (0, 0, 0))]
        paired = pair_residues(c1, c2)
        assert sequence_identity(paired) == 0.5

    def test_empty(self):
        assert sequence_identity([]) == 0.0
```

(Tests for `sasa_deltas`, `ss_changes`, `kabsch_transform`, `rotation_angle_deg` are added in Tasks 6 and 7 — the module skeleton must expose them as importable names now so this file imports cleanly.)

- [ ] **Step 2: Run the failing tests**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_metrics.py -v`
Expected: ImportError — module not found.

- [ ] **Step 3: Implement `compare_structures/metrics.py`**

Create `compare_structures/metrics.py`:
```python
"""Residue pairing and geometric/statistical metrics for compare-structures."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class PairedResidue:
    chain_id: str
    res_num: int
    res_name_1: str
    res_name_2: str
    ca_coord_1: np.ndarray
    ca_coord_2: np.ndarray
    sasa_1: float
    sasa_2: float
    ss_1: str
    ss_2: str
    altloc_1: tuple[str, ...] = field(default_factory=tuple)
    altloc_2: tuple[str, ...] = field(default_factory=tuple)
    max_occupancy_1: float = 1.0
    max_occupancy_2: float = 1.0


def pair_residues(
    chain_1: list[dict],
    chain_2: list[dict],
) -> list[PairedResidue]:
    """Pair residues of two chain-residue lists by residue number.

    Residues present in only one chain are dropped. Residues where the residue
    name differs (i.e. mutations) are still paired — the pairing is purely by
    number. Output is sorted by residue number ascending.
    """
    by_num_1 = {r["res_num"]: r for r in chain_1}
    by_num_2 = {r["res_num"]: r for r in chain_2}
    common_nums = sorted(set(by_num_1) & set(by_num_2))
    paired: list[PairedResidue] = []
    for num in common_nums:
        r1, r2 = by_num_1[num], by_num_2[num]
        paired.append(
            PairedResidue(
                chain_id=r1.get("chain_id", ""),
                res_num=num,
                res_name_1=r1["res_name"],
                res_name_2=r2["res_name"],
                ca_coord_1=np.asarray(r1["ca_coord"], dtype=float),
                ca_coord_2=np.asarray(r2["ca_coord"], dtype=float),
                sasa_1=float(r1.get("sasa", 0.0)),
                sasa_2=float(r2.get("sasa", 0.0)),
                ss_1=r1.get("ss_type", "C"),
                ss_2=r2.get("ss_type", "C"),
                altloc_1=tuple(r1.get("altloc_ids", []) or []),
                altloc_2=tuple(r2.get("altloc_ids", []) or []),
                max_occupancy_1=float(r1.get("max_occupancy", 1.0)),
                max_occupancy_2=float(r2.get("max_occupancy", 1.0)),
            )
        )
    return paired


def displacement(paired: list[PairedResidue]) -> np.ndarray:
    """Per-pair Cα displacement magnitude in Å."""
    if not paired:
        return np.zeros(0, dtype=float)
    diffs = np.stack([p.ca_coord_2 - p.ca_coord_1 for p in paired])
    return np.linalg.norm(diffs, axis=1)


def rmsd(paired: list[PairedResidue]) -> float:
    """RMSD over all paired Cα positions."""
    d = displacement(paired)
    if d.size == 0:
        return 0.0
    return float(np.sqrt((d**2).mean()))


def sequence_identity(paired: list[PairedResidue]) -> float:
    """Fraction of paired residues whose residue names match."""
    if not paired:
        return 0.0
    matches = sum(1 for p in paired if p.res_name_1 == p.res_name_2)
    return matches / len(paired)


# Stubs — implementations land in Tasks 6, 7, 8.
def sasa_deltas(paired, min_abs_delta):  # noqa: ARG001
    raise NotImplementedError


def ss_changes(paired):  # noqa: ARG001
    raise NotImplementedError


def kabsch_transform(points_1, points_2):  # noqa: ARG001
    raise NotImplementedError


def rotation_angle_deg(R):  # noqa: ARG001
    raise NotImplementedError
```

- [ ] **Step 4: Run the tests until green**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_metrics.py -v`
Expected: pairing, displacement, rmsd, sequence_identity tests all PASS (~13 tests). The not-yet-implemented functions are not exercised in this file yet.

- [ ] **Step 5: Commit**

```bash
git add compare_structures/metrics.py tests/test_metrics.py
git commit -m "feat: add residue pairing, displacement, RMSD, sequence identity"
```

---

## Task 6: `metrics.py` — SASA deltas and SS changes

**Files:**
- Modify: `compare_structures/metrics.py`
- Modify: `tests/test_metrics.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_metrics.py` (before the end of the file):
```python
class TestSasaDeltas:
    def test_filters_small_changes(self):
        c1 = [
            _make_residue(1, "A", (0, 0, 0), sasa=100.0),
            _make_residue(2, "B", (0, 0, 0), sasa=200.0),
            _make_residue(3, "C", (0, 0, 0), sasa=50.0),
        ]
        c2 = [
            _make_residue(1, "A", (0, 0, 0), sasa=105.0),   # delta +5  (below)
            _make_residue(2, "B", (0, 0, 0), sasa=150.0),   # delta -50 (above)
            _make_residue(3, "C", (0, 0, 0), sasa=90.0),    # delta +40 (above)
        ]
        paired = pair_residues(c1, c2)
        total, decreases, increases = sasa_deltas(paired, min_abs_delta=30.0)
        assert abs(total - (-5)) < 1e-9  # 5 - 50 + 40
        assert len(decreases) == 1
        assert decreases[0][0].res_num == 2
        assert abs(decreases[0][1] - (-50.0)) < 1e-9
        assert len(increases) == 1
        assert increases[0][0].res_num == 3

    def test_empty_paired(self):
        total, dec, inc = sasa_deltas([], min_abs_delta=30.0)
        assert total == 0.0
        assert dec == []
        assert inc == []


class TestSsChanges:
    def test_detects_helix_to_coil(self):
        c1 = [_make_residue(1, "A", (0, 0, 0), ss="H"),
              _make_residue(2, "B", (0, 0, 0), ss="H")]
        c2 = [_make_residue(1, "A", (0, 0, 0), ss="H"),
              _make_residue(2, "B", (0, 0, 0), ss="C")]
        paired = pair_residues(c1, c2)
        changes = ss_changes(paired)
        assert len(changes) == 1
        assert changes[0].res_num == 2
        assert changes[0].ss_1 == "H"
        assert changes[0].ss_2 == "C"

    def test_no_changes(self):
        c1 = [_make_residue(1, "A", (0, 0, 0), ss="H")]
        c2 = [_make_residue(1, "A", (0, 0, 0), ss="H")]
        assert ss_changes(pair_residues(c1, c2)) == []
```

- [ ] **Step 2: Run the failing tests**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_metrics.py -v`
Expected: new tests FAIL with `NotImplementedError`.

- [ ] **Step 3: Implement in `compare_structures/metrics.py`**

In `compare_structures/metrics.py`, replace the stubs for `sasa_deltas` and `ss_changes` with:
```python
def sasa_deltas(
    paired: list[PairedResidue],
    min_abs_delta: float,
) -> tuple[float, list[tuple[PairedResidue, float]], list[tuple[PairedResidue, float]]]:
    """Compute total ΔSASA and per-residue filtered lists of decreases and increases.

    Returns (total_delta, decreases, increases).
      - total_delta: sum over all paired residues of (sasa_2 - sasa_1), in Å².
      - decreases: sorted ascending (most negative first), filtered by |delta| >= min_abs_delta.
      - increases: sorted descending (most positive first), same filter.
    Each list element is (PairedResidue, delta).
    """
    if not paired:
        return 0.0, [], []
    deltas = [(p, p.sasa_2 - p.sasa_1) for p in paired]
    total = float(sum(d for _, d in deltas))
    filtered = [(p, d) for p, d in deltas if abs(d) >= min_abs_delta]
    decreases = sorted((x for x in filtered if x[1] < 0), key=lambda x: x[1])
    increases = sorted((x for x in filtered if x[1] > 0), key=lambda x: -x[1])
    return total, decreases, increases


def ss_changes(paired: list[PairedResidue]) -> list[PairedResidue]:
    """Return paired residues where the normalized SS type differs."""
    return [p for p in paired if p.ss_1 != p.ss_2]
```

- [ ] **Step 4: Run all metric tests until green**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_metrics.py -v`
Expected: all metric tests PASS.

- [ ] **Step 5: Commit**

```bash
git add compare_structures/metrics.py tests/test_metrics.py
git commit -m "feat: add SASA delta computation and SS change detection"
```

---

## Task 7: `metrics.py` — Kabsch transform and rotation angle

**Files:**
- Modify: `compare_structures/metrics.py`
- Modify: `tests/test_metrics.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_metrics.py`:
```python
class TestKabsch:
    def test_identity_gives_identity_rotation(self):
        points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
        R, t = kabsch_transform(points, points)
        assert np.allclose(R, np.eye(3), atol=1e-9)
        assert np.allclose(t, np.zeros(3), atol=1e-9)

    def test_pure_translation(self):
        p1 = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
        shift = np.array([5, -3, 2], dtype=float)
        p2 = p1 + shift
        R, t = kabsch_transform(p1, p2)
        assert np.allclose(R, np.eye(3), atol=1e-9)
        assert np.allclose(t, shift, atol=1e-9)

    def test_90_deg_rotation_about_z(self):
        p1 = np.array([[1, 0, 0], [0, 1, 0], [-1, 0, 0], [0, -1, 0]], dtype=float)
        # Rotate 90 deg around z: (x,y,z) -> (-y, x, z)
        p2 = np.array([[0, 1, 0], [-1, 0, 0], [0, -1, 0], [1, 0, 0]], dtype=float)
        R, t = kabsch_transform(p1, p2)
        expected = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], dtype=float)
        assert np.allclose(R, expected, atol=1e-9)
        assert np.allclose(t, np.zeros(3), atol=1e-9)


class TestRotationAngleDeg:
    def test_identity(self):
        assert abs(rotation_angle_deg(np.eye(3))) < 1e-9

    def test_90_deg(self):
        R = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], dtype=float)
        assert abs(rotation_angle_deg(R) - 90.0) < 1e-9

    def test_180_deg(self):
        R = np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]], dtype=float)
        assert abs(rotation_angle_deg(R) - 180.0) < 1e-9
```

- [ ] **Step 2: Run the failing tests**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_metrics.py -v`
Expected: new tests FAIL with `NotImplementedError`.

- [ ] **Step 3: Implement in `compare_structures/metrics.py`**

In `compare_structures/metrics.py`, replace the `kabsch_transform` and `rotation_angle_deg` stubs with:
```python
def kabsch_transform(
    points_1: np.ndarray,
    points_2: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Optimal rigid transform mapping points_1 onto points_2 (Kabsch algorithm).

    Returns (R, t) where ``points_1 @ R.T + t`` best approximates ``points_2``
    in a least-squares sense. Both inputs must be shape (N, 3) with N >= 3.
    The rotation matrix is guaranteed to have determinant +1 (no reflections).
    """
    points_1 = np.asarray(points_1, dtype=float)
    points_2 = np.asarray(points_2, dtype=float)
    if points_1.shape != points_2.shape:
        raise ValueError(
            f"shape mismatch: {points_1.shape} vs {points_2.shape}"
        )
    if points_1.ndim != 2 or points_1.shape[1] != 3:
        raise ValueError(f"expected (N, 3) arrays, got {points_1.shape}")
    if points_1.shape[0] < 3:
        raise ValueError(f"need at least 3 points, got {points_1.shape[0]}")

    c1 = points_1.mean(axis=0)
    c2 = points_2.mean(axis=0)
    q1 = points_1 - c1
    q2 = points_2 - c2

    H = q1.T @ q2
    U, _s, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    D = np.diag([1.0, 1.0, d])
    R = Vt.T @ D @ U.T
    t = c2 - R @ c1
    return R, t


def rotation_angle_deg(R: np.ndarray) -> float:
    """Extract the rotation angle (degrees) from a 3x3 rotation matrix."""
    R = np.asarray(R, dtype=float)
    trace = np.trace(R)
    cos_theta = (trace - 1.0) / 2.0
    cos_theta = float(np.clip(cos_theta, -1.0, 1.0))
    return float(np.degrees(np.arccos(cos_theta)))
```

- [ ] **Step 4: Run all metric tests until green**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_metrics.py -v`
Expected: all metric tests PASS.

- [ ] **Step 5: Commit**

```bash
git add compare_structures/metrics.py tests/test_metrics.py
git commit -m "feat: add Kabsch transform and rotation angle extraction"
```

---

## Task 8: `compare_structures/thresholds.py` — constants and drill-down logic

**Files:**
- Create: `compare_structures/thresholds.py`
- Create: `tests/test_thresholds.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_thresholds.py`:
```python
"""Tests for compare_structures.thresholds."""

from compare_structures.thresholds import (
    DRILL_DOWN_RMSD_THRESHOLD,
    NEARLY_IDENTICAL_RMSD,
    compute_drill_down_flags,
    detect_soft_condition,
)


class TestComputeDrillDownFlags:
    def test_small_rmsd_no_drill_down(self):
        flags = compute_drill_down_flags(
            overall_rmsd=0.8, n_moved_regions=0, total_sasa_delta=5.0
        )
        assert flags["report_residue_level"] is False
        assert flags["report_sasa"] is False
        assert flags["report_ss_changes"] is True
        assert "report_residue_level" not in flags["reasons"]

    def test_large_rmsd_drills_down(self):
        flags = compute_drill_down_flags(
            overall_rmsd=5.5, n_moved_regions=2, total_sasa_delta=400.0
        )
        assert flags["report_residue_level"] is True
        assert flags["report_sasa"] is True
        assert "report_residue_level" in flags["reasons"]
        assert "2.0" in flags["reasons"]["report_residue_level"]

    def test_large_sasa_alone_reports_sasa(self):
        flags = compute_drill_down_flags(
            overall_rmsd=1.0, n_moved_regions=0, total_sasa_delta=-500.0
        )
        assert flags["report_residue_level"] is False
        assert flags["report_sasa"] is True


class TestDetectSoftCondition:
    def test_nearly_identical(self):
        assert detect_soft_condition(overall_rmsd=0.1, n_moved_regions=0) == "structures_nearly_identical"

    def test_exactly_at_nearly_identical_boundary(self):
        # Strict < means 0.5 itself is NOT nearly identical.
        assert detect_soft_condition(overall_rmsd=0.5, n_moved_regions=0) is None

    def test_diffuse_motion(self):
        # RMSD above drill-down threshold but no regions found
        assert detect_soft_condition(overall_rmsd=3.0, n_moved_regions=0) == "diffuse_motion"

    def test_clear_conformational_change(self):
        assert detect_soft_condition(overall_rmsd=5.0, n_moved_regions=2) is None

    def test_medium_rmsd_no_soft_condition(self):
        # Between nearly-identical and drill-down thresholds
        assert detect_soft_condition(overall_rmsd=1.2, n_moved_regions=0) is None


def test_thresholds_are_numeric_constants():
    assert isinstance(DRILL_DOWN_RMSD_THRESHOLD, float)
    assert isinstance(NEARLY_IDENTICAL_RMSD, float)
    assert NEARLY_IDENTICAL_RMSD < DRILL_DOWN_RMSD_THRESHOLD
```

- [ ] **Step 2: Run the failing tests**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_thresholds.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `compare_structures/thresholds.py`**

Create `compare_structures/thresholds.py`:
```python
"""Threshold constants and drill-down decision logic."""

from __future__ import annotations

# Thresholds — see design spec §7.
DRILL_DOWN_RMSD_THRESHOLD: float = 2.0     # Å
NEARLY_IDENTICAL_RMSD: float = 0.5         # Å
MIN_MOVED_DISPLACEMENT: float = 3.0        # Å
MIN_REGION_LENGTH: int = 3                 # residues
GAP_TOLERANCE: int = 3                     # residues
SASA_REPORT_THRESHOLD: float = 30.0        # Å² per residue
SASA_TOTAL_REPORT_THRESHOLD: float = 100.0 # Å² total
LOW_IDENTITY_THRESHOLD: float = 0.30       # fraction
DEFAULT_TIMEOUT_SECONDS: int = 1800


def compute_drill_down_flags(
    overall_rmsd: float,
    n_moved_regions: int,  # noqa: ARG001
    total_sasa_delta: float,
) -> dict:
    """Decide which adaptive sections of the report to emit.

    - report_residue_level: True if overall RMSD exceeds the drill-down threshold.
    - report_sasa:          True if |total ΔSASA| exceeds the global threshold.
    - report_ss_changes:    Always True — SS changes are listed in full when present.
    The ``reasons`` dict carries a short text for each True flag, to be echoed
    verbatim in the final report.
    """
    flags: dict = {
        "report_residue_level": False,
        "report_sasa": False,
        "report_ss_changes": True,
        "reasons": {},
    }
    if overall_rmsd > DRILL_DOWN_RMSD_THRESHOLD:
        flags["report_residue_level"] = True
        flags["reasons"]["report_residue_level"] = (
            f"overall RMSD {overall_rmsd:.2f} \u00c5 > threshold "
            f"{DRILL_DOWN_RMSD_THRESHOLD} \u00c5"
        )
    if abs(total_sasa_delta) > SASA_TOTAL_REPORT_THRESHOLD:
        flags["report_sasa"] = True
        flags["reasons"]["report_sasa"] = (
            f"|total \u0394SASA| {abs(total_sasa_delta):.1f} \u00c5\u00b2 > threshold "
            f"{SASA_TOTAL_REPORT_THRESHOLD}"
        )
    return flags


def detect_soft_condition(
    overall_rmsd: float,
    n_moved_regions: int,
) -> str | None:
    """Return a soft-condition label or None.

    See design spec §8.3 for the full set of soft conditions.
    """
    if overall_rmsd < NEARLY_IDENTICAL_RMSD:
        return "structures_nearly_identical"
    if overall_rmsd > DRILL_DOWN_RMSD_THRESHOLD and n_moved_regions == 0:
        return "diffuse_motion"
    return None
```

- [ ] **Step 4: Run the tests until green**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_thresholds.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add compare_structures/thresholds.py tests/test_thresholds.py
git commit -m "feat: add threshold constants and drill-down/soft-condition logic"
```

---

## Task 9: `compare_structures/errors.py` — error.json writer

**Files:**
- Create: `compare_structures/errors.py`
- Create: `tests/test_errors.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_errors.py`:
```python
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
```

- [ ] **Step 2: Run the failing tests**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_errors.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `compare_structures/errors.py`**

Create `compare_structures/errors.py`:
```python
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
```

- [ ] **Step 4: Run the tests until green**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_errors.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add compare_structures/errors.py tests/test_errors.py
git commit -m "feat: add error.json writer with schema-validated output"
```

---

## Task 10: `compare_structures/facts_builder.py` — assemble facts.json

**Files:**
- Create: `compare_structures/facts_builder.py`
- Create: `tests/test_facts_builder.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_facts_builder.py`:
```python
"""Tests for compare_structures.facts_builder."""

import json
from pathlib import Path

import pytest
from jsonschema import validate

from compare_structures.facts_builder import build_facts


def _schema():
    p = Path(__file__).parent.parent / "schemas" / "facts.schema.json"
    return json.loads(p.read_text())


def _make_raw(disps_per_residue, n=10, chain="A"):
    """Build a raw.json-shaped dict with two 'models' of one chain.

    disps_per_residue: iterable of length n with target Cα displacement magnitudes.
    Residue i has ca_coord_1=(0,0,0) and ca_coord_2=(d,0,0).
    """
    res_1 = []
    res_2 = []
    for i, d in enumerate(disps_per_residue, start=1):
        res_1.append({
            "chain_id": chain,
            "res_num": i,
            "res_name": "ALA",
            "ca_coord": [0.0, 0.0, 0.0],
            "sasa": 100.0,
            "ss_type": "C",
            "altloc_ids": [],
            "max_occupancy": 1.0,
        })
        res_2.append({
            "chain_id": chain,
            "res_num": i,
            "res_name": "ALA",
            "ca_coord": [float(d), 0.0, 0.0],
            "sasa": 100.0,
            "ss_type": "C",
            "altloc_ids": [],
            "max_occupancy": 1.0,
        })
    return {
        "input1": {"id": "test_a", "source": "file", "model_id": 1},
        "input2": {"id": "test_b", "source": "file", "model_id": 2},
        "matchmaker": {
            "reference_model": 1, "moved_model": 2,
            "full_rmsd": 0.0, "final_rmsd": 0.0,
            "n_full_pairs": n, "n_final_pairs": n,
            "per_chain": [],
        },
        "chains": [
            {"chain_id": chain, "model": 1, "residues": res_1},
            {"chain_id": chain, "model": 2, "residues": res_2},
        ],
        "chimerax_version": "1.11.1",
        "schema_version": "1.0",
    }


def test_build_facts_emits_valid_schema(tmp_path):
    raw = _make_raw([0.1, 0.2, 4.0, 5.0, 6.0, 5.0, 4.0, 0.3, 0.2, 0.1])
    facts = build_facts(raw, tmp_path)
    validate(facts, _schema())
    assert (tmp_path / "facts.json").is_file()


def test_build_facts_computes_overall_rmsd(tmp_path):
    raw = _make_raw([1.0] * 5)  # all pairs displaced by 1 Å
    facts = build_facts(raw, tmp_path)
    assert abs(facts["alignment"]["overall_rmsd_angstrom"] - 1.0) < 1e-6
    assert facts["alignment"]["n_aligned_residues"] == 5
    assert facts["alignment"]["sequence_identity"] == 1.0


def test_build_facts_detects_single_moved_region(tmp_path):
    raw = _make_raw([0.1, 0.1, 4.0, 5.0, 6.0, 5.0, 4.0, 0.1, 0.1, 0.1])
    facts = build_facts(raw, tmp_path)
    assert len(facts["moved_regions"]) == 1
    region = facts["moved_regions"][0]
    assert region["residue_range"] == [3, 7]
    assert region["n_residues"] == 5


def test_build_facts_nearly_identical_soft_condition(tmp_path):
    raw = _make_raw([0.0] * 10)
    facts = build_facts(raw, tmp_path)
    assert facts["condition"] == "structures_nearly_identical"
    assert facts["moved_regions"] == []


def test_build_facts_altloc_extraction(tmp_path):
    raw = _make_raw([0.1] * 5)
    raw["chains"][0]["residues"][2]["altloc_ids"] = ["A", "B"]
    raw["chains"][0]["residues"][2]["max_occupancy"] = 0.6
    facts = build_facts(raw, tmp_path)
    s1_altlocs = facts["altloc_residues"]["structure_1"]
    assert len(s1_altlocs) == 1
    assert s1_altlocs[0]["res_num"] == 3
    assert s1_altlocs[0]["altloc_ids"] == ["A", "B"]
    assert abs(s1_altlocs[0]["max_occupancy"] - 0.6) < 1e-9


def test_build_facts_ss_change_detection(tmp_path):
    raw = _make_raw([0.1] * 5)
    raw["chains"][0]["residues"][1]["ss_type"] = "H"
    raw["chains"][1]["residues"][1]["ss_type"] = "C"
    facts = build_facts(raw, tmp_path)
    ss = facts["ss_changes"]
    assert len(ss) == 1
    assert ss[0]["res_num"] == 2
    assert ss[0]["ss_before"] == "H"
    assert ss[0]["ss_after"] == "C"


def test_build_facts_top_movers_sorted(tmp_path):
    raw = _make_raw([0.1, 10.0, 0.1, 5.0, 0.1])
    facts = build_facts(raw, tmp_path)
    top = facts["top_ca_movers"]
    assert top[0]["res_num"] == 2
    assert abs(top[0]["displacement"] - 10.0) < 1e-6
    assert top[1]["res_num"] == 4
```

- [ ] **Step 2: Run the failing tests**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_facts_builder.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `compare_structures/facts_builder.py`**

Create `compare_structures/facts_builder.py`:
```python
"""Build the facts.json payload from a raw.json dict."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from jsonschema import validate

from .clustering import cluster_moved_regions
from .metrics import (
    PairedResidue,
    displacement,
    kabsch_transform,
    pair_residues,
    rmsd,
    rotation_angle_deg,
    sasa_deltas,
    sequence_identity,
    ss_changes,
)
from .thresholds import (
    GAP_TOLERANCE,
    LOW_IDENTITY_THRESHOLD,
    MIN_MOVED_DISPLACEMENT,
    MIN_REGION_LENGTH,
    SASA_REPORT_THRESHOLD,
    compute_drill_down_flags,
    detect_soft_condition,
)

_SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "facts.schema.json"
_FACTS_SCHEMA_VERSION = "1.0"


def build_facts(raw: dict, output_dir: Path) -> dict:
    """Compute facts.json from raw.json-shaped data and write it to output_dir.

    Returns the facts dict (also written to ``output_dir/facts.json``).
    Validates against schemas/facts.schema.json; raises on schema mismatch.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Index raw chains by (model, chain_id).
    m1_by_chain: dict[str, list[dict]] = {}
    m2_by_chain: dict[str, list[dict]] = {}
    for chain_entry in raw["chains"]:
        cid = chain_entry["chain_id"]
        for r in chain_entry["residues"]:
            r.setdefault("chain_id", cid)
        if chain_entry["model"] == 1:
            m1_by_chain[cid] = chain_entry["residues"]
        elif chain_entry["model"] == 2:
            m2_by_chain[cid] = chain_entry["residues"]

    chain_summaries: list[dict] = []
    moved_regions_all: list[dict] = []
    all_paired: list[PairedResidue] = []

    common_chains = sorted(set(m1_by_chain) & set(m2_by_chain))
    for chain_id in common_chains:
        paired = pair_residues(m1_by_chain[chain_id], m2_by_chain[chain_id])
        if not paired:
            continue
        all_paired.extend(paired)

        disps = displacement(paired)
        res_nums = [p.res_num for p in paired]
        regions = cluster_moved_regions(
            chain_id,
            res_nums,
            disps,
            min_displacement=MIN_MOVED_DISPLACEMENT,
            min_length=MIN_REGION_LENGTH,
            gap_tolerance=GAP_TOLERANCE,
        )

        region_dicts: list[dict] = []
        for region in regions:
            region_paired = [
                p for p in paired
                if region.residue_range[0] <= p.res_num <= region.residue_range[1]
            ]
            coords_1 = np.stack([p.ca_coord_1 for p in region_paired])
            coords_2 = np.stack([p.ca_coord_2 for p in region_paired])

            rot_deg: float | None = None
            trans_mag: float | None = None
            if len(region_paired) >= 3:
                try:
                    R, t = kabsch_transform(coords_1, coords_2)
                    rot_deg = round(rotation_angle_deg(R), 2)
                    trans_mag = round(float(np.linalg.norm(t)), 3)
                except ValueError:
                    # Degenerate (collinear) point set — leave None.
                    pass

            region_dicts.append(
                {
                    "chain_id": region.chain_id,
                    "residue_range": list(region.residue_range),
                    "residue_range_label": (
                        f"{region.chain_id}/{region.residue_range[0]}-{region.residue_range[1]}"
                    ),
                    "n_residues": region.n_residues,
                    "mean_ca_displacement": round(region.mean_displacement, 3),
                    "max_ca_displacement": round(region.max_displacement, 3),
                    "estimated_rotation_deg": rot_deg,
                    "estimated_translation_angstrom": trans_mag,
                    "hinge_candidate_residues": [
                        region.residue_range[0] - 1,
                        region.residue_range[1] + 1,
                    ],
                }
            )
        moved_regions_all.extend(region_dicts)

        chain_summaries.append(
            {
                "chain_id": chain_id,
                "n_residues": len(paired),
                "ca_displacement_stats": {
                    "mean": round(float(disps.mean()), 3),
                    "median": round(float(np.median(disps)), 3),
                    "max": round(float(disps.max()), 3),
                    "p95": round(float(np.percentile(disps, 95)), 3),
                },
                "significant_change": len(region_dicts) > 0,
            }
        )

    overall_rmsd = rmsd(all_paired)
    seq_id = sequence_identity(all_paired)
    total_delta, decreases, increases = sasa_deltas(all_paired, SASA_REPORT_THRESHOLD)
    ss_change_list = ss_changes(all_paired)

    # Top-10 Cα movers across all chains.
    all_disps = displacement(all_paired) if all_paired else np.zeros(0)
    if all_disps.size:
        order = np.argsort(-all_disps)[:10]
    else:
        order = np.zeros(0, dtype=int)
    top_movers = [
        {
            "chain_id": all_paired[i].chain_id,
            "res_num": all_paired[i].res_num,
            "res_name": all_paired[i].res_name_1,
            "displacement": round(float(all_disps[i]), 3),
        }
        for i in order
    ]

    drill_flags = compute_drill_down_flags(
        overall_rmsd, len(moved_regions_all), total_delta
    )
    condition = detect_soft_condition(overall_rmsd, len(moved_regions_all))

    warnings: list[str] = []
    if all_paired and seq_id < LOW_IDENTITY_THRESHOLD:
        warnings.append(f"low_sequence_identity_{seq_id:.2f}")

    altloc_1: list[dict] = []
    altloc_2: list[dict] = []
    for p in all_paired:
        if p.altloc_1:
            altloc_1.append(
                {
                    "chain_id": p.chain_id,
                    "res_num": p.res_num,
                    "res_name": p.res_name_1,
                    "altloc_ids": list(p.altloc_1),
                    "max_occupancy": p.max_occupancy_1,
                }
            )
        if p.altloc_2:
            altloc_2.append(
                {
                    "chain_id": p.chain_id,
                    "res_num": p.res_num,
                    "res_name": p.res_name_2,
                    "altloc_ids": list(p.altloc_2),
                    "max_occupancy": p.max_occupancy_2,
                }
            )

    mm = raw.get("matchmaker", {})
    alignment_section: dict = {
        "method": "matchmaker",
        "reference": raw["input1"].get("id"),
        "moved": raw["input2"].get("id"),
        "overall_rmsd_angstrom": round(overall_rmsd, 3),
        "n_aligned_residues": len(all_paired),
        "sequence_identity": round(seq_id, 4),
    }
    if "final_rmsd" in mm:
        alignment_section["refined_rmsd_angstrom"] = round(float(mm["final_rmsd"]), 3)

    facts: dict = {
        "inputs": {"structure_1": raw["input1"], "structure_2": raw["input2"]},
        "alignment": alignment_section,
        "chain_summary": chain_summaries,
        "moved_regions": moved_regions_all,
        "top_ca_movers": top_movers,
        "sasa_changes": {
            "total_delta_angstrom2": round(total_delta, 2),
            "top_decreases": [
                {
                    "chain_id": p.chain_id,
                    "res_num": p.res_num,
                    "res_name": p.res_name_1,
                    "delta_sasa": round(d, 2),
                }
                for p, d in decreases[:10]
            ],
            "top_increases": [
                {
                    "chain_id": p.chain_id,
                    "res_num": p.res_num,
                    "res_name": p.res_name_1,
                    "delta_sasa": round(d, 2),
                }
                for p, d in increases[:10]
            ],
        },
        "ss_changes": [
            {
                "chain_id": p.chain_id,
                "res_num": p.res_num,
                "res_name": p.res_name_1,
                "ss_before": p.ss_1,
                "ss_after": p.ss_2,
            }
            for p in ss_change_list
        ],
        "altloc_residues": {"structure_1": altloc_1, "structure_2": altloc_2},
        "drill_down_flags": drill_flags,
        "warnings": warnings,
        "condition": condition,
        "artifacts": {"aligned_structure": "aligned.cif"},
        "meta": {
            "schema_version": _FACTS_SCHEMA_VERSION,
            "chimerax_version": raw.get("chimerax_version", "unknown"),
            "generated_at": datetime.now(UTC).isoformat(),
        },
    }

    schema = json.loads(_SCHEMA_PATH.read_text())
    validate(facts, schema)
    (output_dir / "facts.json").write_text(json.dumps(facts, indent=2))
    return facts
```

- [ ] **Step 4: Run the tests until green**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_facts_builder.py -v`
Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add compare_structures/facts_builder.py tests/test_facts_builder.py
git commit -m "feat: assemble facts.json from raw data with schema validation"
```

---

## Task 11: `compare_structures/chimerax_runner.py` — subprocess orchestration

**Files:**
- Create: `compare_structures/chimerax_runner.py`
- Create: `tests/test_chimerax_runner.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_chimerax_runner.py`:
```python
"""Tests for compare_structures.chimerax_runner (subprocess logic, mocked)."""

import json
import subprocess
from pathlib import Path
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
        with patch("subprocess.run", side_effect=_raise):
            with pytest.raises(ChimeraxTimeoutError):
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
        # The --script argument is a single shell-quoted string combining script path and args.
        script_arg = captured["cmd"][script_idx]
        assert str(script) in script_arg
        assert "a" in script_arg
        assert "b" in script_arg
        assert captured["kwargs"]["timeout"] == 123


def test_chimerax_run_error_has_stderr_attr():
    e = ChimeraxRunError("x", stderr_tail="stuff")
    assert e.stderr_tail == "stuff"
```

- [ ] **Step 2: Run the failing tests**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_chimerax_runner.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `compare_structures/chimerax_runner.py`**

Create `compare_structures/chimerax_runner.py`:
```python
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
```

- [ ] **Step 4: Run the tests until green**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_chimerax_runner.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add compare_structures/chimerax_runner.py tests/test_chimerax_runner.py
git commit -m "feat: add headless ChimeraX subprocess orchestrator"
```

---

## Task 12: `chimerax_script.py` — ChimeraX-side extraction

**Files:**
- Create: `chimerax_script.py`

No unit test — this script runs inside ChimeraX and is covered by integration tests in Task 14.

- [ ] **Step 1: Create `chimerax_script.py`**

Create `chimerax_script.py`:
```python
"""Run inside ChimeraX to open two structures, run matchmaker, extract data,
save aligned.cif, and write raw.json.

Invocation (from chimerax_runner.py):
  chimerax --nogui --exit --silent --script \
    "chimerax_script.py <in1> <in2> <raw_json_out> <aligned_cif_out> <chain1> <chain2>"

Each of <in1>, <in2> is either a 4-character PDB ID or an absolute file path.
<chain1>, <chain2> are chain IDs to restrict matchmaker to, or "" (empty
string) for auto.

The script exits with code 0 on success, non-zero on failure; on failure, a
structured one-line JSON error is printed to stderr so the parent analyze.py
can capture it.
"""

from __future__ import annotations

import json
import sys
import traceback

# The ChimeraX session is provided in the script's global scope as 'session'.
# We rebind it here to satisfy static analyzers — it is set by ChimeraX itself.
session = globals().get("session")  # noqa: F811


def _emit_error(error_type: str, message: str) -> None:
    sys.stderr.write(json.dumps({"error_type": error_type, "message": message}) + "\n")
    sys.stderr.flush()


def _normalize_ss(ss_int: int) -> str:
    # ChimeraX Residue.ss_type: 0=coil/other, 1=helix, 2=strand.
    if ss_int == 1:
        return "H"
    if ss_int == 2:
        return "E"
    return "C"


def _classify_input(arg: str) -> dict:
    import os
    if len(arg) == 4 and arg[0].isdigit() and arg.isalnum():
        return {"id": arg.upper(), "source": "pdb_id"}
    return {"id": os.path.splitext(os.path.basename(arg))[0], "source": "file", "path": arg}


def _open_input(arg: str, classify: dict):
    from chimerax.core.commands import run
    if classify["source"] == "pdb_id":
        return run(session, f"open {classify['id']}")[0]
    return run(session, f"open {classify['path']}")[0]


def _filter_by_chain(model, chain_id: str):
    """Return the atoms of ``model`` restricted to ``chain_id`` (empty string = all)."""
    if not chain_id:
        return model.atoms
    mask = model.atoms.residues.chain_ids == chain_id
    filtered = model.atoms[mask]
    if len(filtered) == 0:
        raise RuntimeError(f"chain {chain_id!r} not found in model")
    return filtered


def _run_matchmaker(model_ref, model_move, chain_ref: str, chain_move: str):
    from chimerax.match_maker.match import cmd_match
    match_atoms = _filter_by_chain(model_move, chain_move)
    ref_atoms = _filter_by_chain(model_ref, chain_ref)
    results = cmd_match(session, match_atoms=match_atoms, to=ref_atoms)
    if not results:
        raise RuntimeError("matchmaker produced no results (structures may be unrelated)")
    return results


def _extract_altloc_info(residue):
    alt_ids: list[str] = []
    max_occ = 0.0
    for atom in residue.atoms:
        occ = float(getattr(atom, "occupancy", 1.0))
        if occ > max_occ:
            max_occ = occ
        alt = getattr(atom, "alt_loc", "")
        if alt and alt not in (" ", ""):
            if alt not in alt_ids:
                alt_ids.append(alt)
    if not alt_ids:
        max_occ = 1.0
    return alt_ids, max_occ


def _collect_residue_data(model, model_idx: int) -> list[dict]:
    # Run measure sasa first so residue.area is populated.
    from chimerax.core.commands import run
    run(session, f"measure sasa #{model_idx}")

    chains_out: dict[str, list[dict]] = {}
    for residue in model.residues:
        principal = residue.principal_atom
        if principal is None:
            continue  # non-polymer or missing Cα
        chain_id = residue.chain_id
        ca = principal.scene_coord  # numpy 3-vector in aligned frame
        alt_ids, max_occ = _extract_altloc_info(residue)
        entry = {
            "chain_id": chain_id,
            "res_num": int(residue.number),
            "res_name": residue.name,
            "ca_coord": [float(ca[0]), float(ca[1]), float(ca[2])],
            "sasa": float(getattr(residue, "area", 0.0)),
            "ss_type": _normalize_ss(int(getattr(residue, "ss_type", 0))),
            "altloc_ids": alt_ids,
            "max_occupancy": float(max_occ),
        }
        chains_out.setdefault(chain_id, []).append(entry)

    return [
        {"chain_id": cid, "model": model_idx, "residues": residues}
        for cid, residues in sorted(chains_out.items())
    ]


def main(argv: list[str]) -> int:
    if len(argv) != 6:
        _emit_error("script_usage", f"expected 6 args, got {len(argv)}: {argv}")
        return 2

    in1, in2, raw_out, aligned_out, chain1, chain2 = argv

    try:
        from chimerax.core.commands import run

        c1 = _classify_input(in1)
        c2 = _classify_input(in2)

        model_1 = _open_input(in1, c1)
        model_2 = _open_input(in2, c2)

        mm_results = _run_matchmaker(
            model_ref=model_1,
            model_move=model_2,
            chain_ref=chain1,
            chain_move=chain2,
        )
        # Aggregate matchmaker stats across all chain-pair matches.
        full_rmsd_weighted_sum = 0.0
        final_rmsd_weighted_sum = 0.0
        n_full_total = 0
        n_final_total = 0
        per_chain = []
        for r in mm_results:
            n_full = len(r["full match atoms"])
            n_final = len(r["final match atoms"])
            full_rmsd_weighted_sum += (float(r["full RMSD"]) ** 2) * n_full
            final_rmsd_weighted_sum += (float(r["final RMSD"]) ** 2) * n_final
            n_full_total += n_full
            n_final_total += n_final
            per_chain.append({
                "n_full": n_full,
                "n_final": n_final,
                "full_rmsd": float(r["full RMSD"]),
                "final_rmsd": float(r["final RMSD"]),
            })
        full_rmsd = (full_rmsd_weighted_sum / n_full_total) ** 0.5 if n_full_total else 0.0
        final_rmsd = (final_rmsd_weighted_sum / n_final_total) ** 0.5 if n_final_total else 0.0

        # Extract per-residue data AFTER matchmaker so scene_coord is aligned.
        chains_1 = _collect_residue_data(model_1, 1)
        chains_2 = _collect_residue_data(model_2, 2)

        # Save aligned mmCIF with both models.
        run(session, f"save {aligned_out} format mmcif models #1,2")

        chimerax_version = "unknown"
        try:
            from chimerax.core import version as _v
            chimerax_version = str(_v)
        except Exception:  # noqa: BLE001
            pass

        raw = {
            "input1": {**c1, "model_id": 1},
            "input2": {**c2, "model_id": 2},
            "matchmaker": {
                "reference_model": 1,
                "moved_model": 2,
                "full_rmsd": float(full_rmsd),
                "final_rmsd": float(final_rmsd),
                "n_full_pairs": int(n_full_total),
                "n_final_pairs": int(n_final_total),
                "per_chain": per_chain,
            },
            "chains": chains_1 + chains_2,
            "chimerax_version": chimerax_version,
            "schema_version": "1.0",
        }
        with open(raw_out, "w") as f:
            json.dump(raw, f, indent=2)
        return 0

    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()
        _emit_error(type(e).__name__, f"{e}\n{tb}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 2: Static smoke check — the file parses as Python**

Run: `uv run --with numpy python -c "import ast; ast.parse(open('chimerax_script.py').read()); print('parses ok')"`
Expected: `parses ok`.

- [ ] **Step 3: Commit**

```bash
git add chimerax_script.py
git commit -m "feat: add chimerax_script.py for nogui ChimeraX extraction"
```

---

## Task 13: `compare_structures/cli.py` and `analyze.py` — entry point

**Files:**
- Create: `compare_structures/cli.py`
- Create: `analyze.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests for cli.py**

Create `tests/test_cli.py`:
```python
"""Tests for compare_structures.cli — end-to-end wiring with mocked ChimeraX."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from compare_structures import cli


def _fake_chimerax_runner_impl(raw_payload, aligned_payload=b"data_test\n"):
    def _run(chimerax_executable, script_path, script_args, timeout_seconds):
        # argv order from cli.main: in1, in2, raw_out, aligned_out
        raw_out = Path(script_args[2])
        aligned_out = Path(script_args[3])
        raw_out.write_text(json.dumps(raw_payload))
        aligned_out.write_bytes(aligned_payload)
        import subprocess
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    return _run


def _minimal_raw(in1_id="1TST", in2_id="2TST"):
    res_1 = [{
        "chain_id": "A", "res_num": i, "res_name": "ALA",
        "ca_coord": [0.0, 0.0, 0.0], "sasa": 100.0, "ss_type": "C",
        "altloc_ids": [], "max_occupancy": 1.0,
    } for i in range(1, 11)]
    res_2 = [{
        "chain_id": "A", "res_num": i, "res_name": "ALA",
        "ca_coord": [float(0.1), 0.0, 0.0], "sasa": 100.0, "ss_type": "C",
        "altloc_ids": [], "max_occupancy": 1.0,
    } for i in range(1, 11)]
    return {
        "input1": {"id": in1_id, "source": "pdb_id", "model_id": 1},
        "input2": {"id": in2_id, "source": "pdb_id", "model_id": 2},
        "matchmaker": {
            "reference_model": 1, "moved_model": 2,
            "full_rmsd": 0.1, "final_rmsd": 0.05,
            "n_full_pairs": 10, "n_final_pairs": 10, "per_chain": [],
        },
        "chains": [
            {"chain_id": "A", "model": 1, "residues": res_1},
            {"chain_id": "A", "model": 2, "residues": res_2},
        ],
        "chimerax_version": "1.11.1",
        "schema_version": "1.0",
    }


class TestCliMain:
    def test_successful_end_to_end(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CHIMERAX_PATH", str(tmp_path / "chimerax"))
        (tmp_path / "chimerax").write_text("")
        raw = _minimal_raw()
        out = tmp_path / "runs" / "out"
        with patch("compare_structures.cli.run_chimerax_script",
                   side_effect=_fake_chimerax_runner_impl(raw)):
            exit_code = cli.main([
                "--in1", "1TST",
                "--in2", "2TST",
                "--out", str(out),
            ], standalone_mode=False)
        assert exit_code == 0
        assert (out / "raw.json").is_file()
        assert (out / "facts.json").is_file()
        assert (out / "aligned.cif").is_file()
        facts = json.loads((out / "facts.json").read_text())
        assert facts["condition"] == "structures_nearly_identical"

    def test_invalid_pdb_writes_error_json(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CHIMERAX_PATH", str(tmp_path / "chimerax"))
        (tmp_path / "chimerax").write_text("")
        out = tmp_path / "runs" / "out"
        exit_code = cli.main([
            "--in1", "xxx",  # not a 4-char PDB id and not a file
            "--in2", "1TST",
            "--out", str(out),
        ], standalone_mode=False)
        assert exit_code != 0
        err = json.loads((out / "error.json").read_text())
        assert err["stage"] == "validation"
        assert "PDB ID" in err["message"] or "pdb id" in err["message"].lower()

    def test_chimerax_failure_writes_error_json(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CHIMERAX_PATH", str(tmp_path / "chimerax"))
        (tmp_path / "chimerax").write_text("")
        from compare_structures.chimerax_runner import ChimeraxRunError
        out = tmp_path / "runs" / "out"
        def _raise(**kwargs):
            raise ChimeraxRunError("boom", stderr_tail="traceback...")
        with patch("compare_structures.cli.run_chimerax_script", side_effect=_raise):
            exit_code = cli.main([
                "--in1", "1TST",
                "--in2", "2TST",
                "--out", str(out),
            ], standalone_mode=False)
        assert exit_code != 0
        err = json.loads((out / "error.json").read_text())
        assert err["stage"] == "chimerax_script"
        assert err["stderr_tail"] == "traceback..."
```

- [ ] **Step 2: Run the failing tests**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_cli.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `compare_structures/cli.py`**

Create `compare_structures/cli.py`:
```python
"""click-based CLI entry point for analyze.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from .chimerax_runner import (
    ChimeraxRunError,
    ChimeraxTimeoutError,
    run_chimerax_script,
)
from .errors import write_error
from .facts_builder import build_facts
from .thresholds import DEFAULT_TIMEOUT_SECONDS
from .validators import (
    InputValidationError,
    resolve_chimerax_executable,
    validate_input,
)


@click.command()
@click.option("--in1", "in1_arg", required=True, help="First structure (PDB ID or file path)")
@click.option("--in2", "in2_arg", required=True, help="Second structure (PDB ID or file path)")
@click.option("--out", "out_arg", required=True, type=click.Path(), help="Output directory")
@click.option(
    "--timeout",
    "timeout_arg",
    default=DEFAULT_TIMEOUT_SECONDS,
    type=int,
    help=f"ChimeraX subprocess timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS})",
)
@click.option(
    "--chain1",
    "chain1_arg",
    default="",
    help="Restrict matchmaker on structure 1 to this chain ID (default: all chains)",
)
@click.option(
    "--chain2",
    "chain2_arg",
    default="",
    help="Restrict matchmaker on structure 2 to this chain ID (default: all chains)",
)
def _cli_command(
    in1_arg: str,
    in2_arg: str,
    out_arg: str,
    timeout_arg: int,
    chain1_arg: str,
    chain2_arg: str,
) -> None:
    code = _run(in1_arg, in2_arg, out_arg, timeout_arg, chain1_arg, chain2_arg)
    sys.exit(code)


def _run(
    in1: str,
    in2: str,
    out: str,
    timeout: int,
    chain1: str = "",
    chain2: str = "",
) -> int:
    output_dir = Path(out).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: validation.
    try:
        norm_1 = validate_input(in1)
        norm_2 = validate_input(in2)
        chimerax_exe = resolve_chimerax_executable()
    except InputValidationError as e:
        write_error(
            output_dir,
            error_type="validation",
            message=str(e),
            stage="validation",
        )
        click.echo(f"validation failed: {e}", err=True)
        return 2

    # Stage 2: ChimeraX subprocess.
    raw_out = output_dir / "raw.json"
    aligned_out = output_dir / "aligned.cif"
    script_path = Path(__file__).resolve().parent.parent / "chimerax_script.py"

    def _arg_for(norm: dict, original: str) -> str:
        if norm["source"] == "pdb_id":
            return norm["id"]
        return str(norm["path"])

    try:
        run_chimerax_script(
            chimerax_executable=chimerax_exe,
            script_path=script_path,
            script_args=[
                _arg_for(norm_1, in1),
                _arg_for(norm_2, in2),
                str(raw_out),
                str(aligned_out),
                chain1,
                chain2,
            ],
            timeout_seconds=timeout,
        )
    except ChimeraxTimeoutError as e:
        write_error(
            output_dir,
            error_type="chimerax_timeout",
            message=str(e),
            stage="chimerax_script",
            stderr_tail=e.stderr_tail,
        )
        click.echo(f"chimerax timeout: {e}", err=True)
        return 3
    except ChimeraxRunError as e:
        write_error(
            output_dir,
            error_type="chimerax_failed",
            message=str(e),
            stage="chimerax_script",
            stderr_tail=e.stderr_tail,
        )
        click.echo(f"chimerax failed: {e}", err=True)
        return 3

    if not raw_out.is_file():
        write_error(
            output_dir,
            error_type="missing_raw_output",
            message="chimerax_script.py did not produce raw.json",
            stage="chimerax_script",
        )
        return 4

    # Stage 3: post-processing.
    try:
        raw = json.loads(raw_out.read_text())
        build_facts(raw, output_dir)
    except Exception as e:  # noqa: BLE001
        write_error(
            output_dir,
            error_type=type(e).__name__,
            message=str(e),
            stage="analyze_post",
        )
        click.echo(f"post-processing failed: {e}", err=True)
        return 5

    click.echo(f"analysis complete: {output_dir}")
    return 0


def main(argv: list[str] | None = None, standalone_mode: bool = True) -> int:
    """Entry point usable both as CLI and from tests.

    When ``standalone_mode`` is False, click parses the args into a context and
    we call ``_run`` directly, returning its exit code instead of calling
    ``sys.exit``.
    """
    if standalone_mode:
        _cli_command.main(args=argv, standalone_mode=True)
        return 0  # unreachable — click will sys.exit

    ctx = _cli_command.make_context("compare-structures", list(argv or []))
    with ctx:
        return _run(
            in1=ctx.params["in1_arg"],
            in2=ctx.params["in2_arg"],
            out=ctx.params["out_arg"],
            timeout=ctx.params["timeout_arg"],
            chain1=ctx.params["chain1_arg"],
            chain2=ctx.params["chain2_arg"],
        )
```

- [ ] **Step 4: Implement `analyze.py`**

Create `analyze.py`:
```python
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
```

- [ ] **Step 5: Make `analyze.py` executable**

Run: `chmod +x analyze.py`
Expected: (no output)

- [ ] **Step 6: Run the cli tests until green**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_cli.py -v`
Expected: all 3 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add compare_structures/cli.py analyze.py tests/test_cli.py
git commit -m "feat: wire CLI entry point with validation + subprocess + post-processing"
```

---

## Task 14: Integration test — 1AKE vs 4AKE

**Files:**
- Create: `tests/test_integration.py`

This test requires ChimeraX. It is marked `@pytest.mark.chimerax` and is skipped when ChimeraX is not resolvable.

- [ ] **Step 1: Write integration tests**

Create `tests/test_integration.py`:
```python
"""Integration tests — require a working ChimeraX installation.

Run locally before pushing:
  uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_integration.py -v -m chimerax

If CHIMERAX_PATH is unset and 'chimerax' is not on PATH, these tests are skipped.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _chimerax_available() -> bool:
    if os.environ.get("CHIMERAX_PATH"):
        return Path(os.environ["CHIMERAX_PATH"]).is_file()
    return shutil.which("chimerax") is not None


pytestmark = [
    pytest.mark.chimerax,
    pytest.mark.skipif(not _chimerax_available(), reason="ChimeraX not found"),
]


def _run_analyze(tmp_path: Path, in1: str, in2: str, out_subdir: str) -> tuple[int, Path]:
    out = tmp_path / out_subdir
    cmd = [
        sys.executable,
        str(_REPO_ROOT / "analyze.py"),
        "--in1", in1,
        "--in2", in2,
        "--out", str(out),
    ]
    # Use python -c to import and call cli.main directly to avoid uv env overhead.
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_REPO_ROOT)
    result = subprocess.run(
        [
            sys.executable, "-c",
            "from compare_structures.cli import main; import sys; "
            "sys.exit(main(sys.argv[1:], standalone_mode=False))",
            "--in1", in1, "--in2", in2, "--out", str(out),
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    return result.returncode, out


def test_1ake_vs_4ake(tmp_path):
    code, out = _run_analyze(tmp_path, "1AKE", "4AKE", "ake")
    assert code == 0, f"stderr: {out}"
    facts = json.loads((out / "facts.json").read_text())

    # Overall metrics (ranges tolerate ChimeraX version drift).
    rmsd = facts["alignment"]["overall_rmsd_angstrom"]
    assert 5.0 <= rmsd <= 7.5, f"unexpected rmsd {rmsd}"
    n_aligned = facts["alignment"]["n_aligned_residues"]
    assert 180 <= n_aligned <= 220, f"unexpected n_aligned {n_aligned}"

    # Drill-down expected for adenylate kinase open/closed.
    assert facts["drill_down_flags"]["report_residue_level"] is True
    assert len(facts["moved_regions"]) >= 2

    # LID domain (118-167) should overlap at least one moved region.
    def overlaps(region, lo, hi):
        r_lo, r_hi = region["residue_range"]
        return not (r_hi < lo - 3 or r_lo > hi + 3)

    assert any(overlaps(r, 118, 167) for r in facts["moved_regions"]), \
        f"no region overlaps LID 118-167: {[r['residue_range_label'] for r in facts['moved_regions']]}"

    # NMP-binding domain (30-59) should overlap at least one moved region.
    assert any(overlaps(r, 30, 59) for r in facts["moved_regions"]), \
        f"no region overlaps NMP 30-59: {[r['residue_range_label'] for r in facts['moved_regions']]}"

    # aligned.cif exists and is non-trivial.
    aligned = out / "aligned.cif"
    assert aligned.is_file()
    assert aligned.stat().st_size > 1000  # rough sanity
```

- [ ] **Step 2: Run the integration test (requires local ChimeraX)**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_integration.py -v -m chimerax`
Expected:
- If ChimeraX is available: `test_1ake_vs_4ake PASSED`
- If not: the test is skipped with the "ChimeraX not found" reason.

If the test fails, investigate:
- Read the last output directory, check `error.json` if present
- Check ChimeraX version via `chimerax --nogui --exit --script "import chimerax.core; print(chimerax.core.version)"`
- Check that `chimerax_script.py` produced a valid `raw.json`

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add 1AKE vs 4AKE integration test"
```

---

## Task 15: Integration tests — identical pair and invalid PDB

**Files:**
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Append new tests**

Append to `tests/test_integration.py`:
```python
def test_identical_pair_soft_condition(tmp_path):
    code, out = _run_analyze(tmp_path, "1AKE", "1AKE", "same")
    assert code == 0
    facts = json.loads((out / "facts.json").read_text())
    assert facts["condition"] == "structures_nearly_identical"
    assert facts["moved_regions"] == []
    assert facts["alignment"]["overall_rmsd_angstrom"] < 0.5


def test_invalid_pdb_id_hard_error(tmp_path):
    code, out = _run_analyze(tmp_path, "9ZZZ", "1AKE", "bad")
    # Validation passes (9ZZZ is a valid 4-char format), ChimeraX fetch fails.
    assert code != 0
    err_path = out / "error.json"
    assert err_path.is_file()
    err = json.loads(err_path.read_text())
    assert err["stage"] == "chimerax_script"
```

- [ ] **Step 2: Run all integration tests**

Run: `uv run --with pytest --with numpy --with jsonschema --with click pytest tests/test_integration.py -v -m chimerax`
Expected: all 3 tests PASS (or skipped if ChimeraX missing).

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add identical-pair and invalid-PDB integration coverage"
```

---

## Task 16: `templates/report_prompt.md` — report-writing prompt

**Files:**
- Create: `templates/report_prompt.md`

- [ ] **Step 1: Write the prompt template**

Create `templates/report_prompt.md`:
```markdown
# 構造比較レポート執筆プロンプト

あなたは `facts.json` を入力として受け取り、日本語で簡潔な構造比較レポートを
`report.md` として書き出す役割です。このレポートはユーザー（構造生物学の研究者）
が読むことを想定しています。

## 厳守ルール（最重要）

以下は例外なく禁止です。違反するとレポート全体が無価値になります。

1. **`facts.json` に含まれていない数値・残基・領域・特徴を、一切レポートに書かない**
2. **文献・先行研究・ジャーナル論文への言及をしない**
   - 禁止フレーズ例: 「〜として知られている」「報告されている」「既知の」
     「よく観察される」「典型的な」「一般に」
3. **機能的・機構的な解釈をしない**
   - 禁止例: 「ATPの結合を促進する」「触媒活性に関与する」「基質認識ポケット」
   - 許可例: 「残基42のCα変位が14.1 Å」「SASAが88 Å² 減少」
4. **名前付きエンティティの知識からの推論をしない**
   - 禁止例: 「P-loop」「ロスマンフォールド」「触媒三残基」「HELIXモチーフ」
   - これらの単語は、たとえ動いた領域の位置と一致していても、一切使わない
5. **動いていない残基・領域には言及しない**
   - `moved_regions` に出現しない残基を詳述しない
   - `top_ca_movers` の上位に出ない残基のCα変位を書かない
6. **形容詞に数値を必ず添える**
   - 禁止例: 「大きな変化」「わずかに動いた」
   - 許可例: 「大きな変化（Cα RMSD 5.53 Å）」「わずかな動き（平均変位 0.8 Å）」

## レポートの構造

以下のセクションを、この順番で書きます。`facts.json` の `drill_down_flags` や
`condition` の値によっては省略するセクションがあります（後述）。

### 1. ヘッダ

- 見出し: 入力2構造のID（`inputs.structure_1.id` と `inputs.structure_2.id`）
- 生成日時（`meta.generated_at` を日本語の読みやすい形に整形）

### 2. 全体要約（Chain level summary）

常に書きます。以下の事実を述べます:

- 解析手法: `alignment.method`（matchmaker）
- 全体 Cα RMSD: `alignment.overall_rmsd_angstrom` Å
- アラインされた残基数: `alignment.n_aligned_residues`
- 配列同一性: `alignment.sequence_identity` をパーセント表記で
- 動いた領域の数: `len(moved_regions)`
- 一行のヘッドライン（数値を必ず含める）

`condition` が `structures_nearly_identical` の場合は「有意な構造変化は検出されず」
と明記し、セクション3は省略してセクション5（警告）に進みます。

`condition` が `diffuse_motion` の場合は「全体RMSDは閾値を超えているが、連続した
動領域は同定されず」と明記します。

### 3. 動いた領域の詳述（Moved-region detail）

`drill_down_flags.report_residue_level` が `true` かつ `len(moved_regions) > 0` の
場合にのみ書きます。

各領域について以下を1段落でまとめます:

- 領域ラベル: `residue_range_label`（例: A/30-59）
- 残基数: `n_residues`
- 平均/最大 Cα 変位: `mean_ca_displacement` / `max_ca_displacement` Å
- 推定回転角: `estimated_rotation_deg`°（null の場合は言及しない）
- 推定並進量: `estimated_translation_angstrom` Å（null の場合は言及しない）
- ヒンジ候補残基: `hinge_candidate_residues`
- 領域内の SS 変化: `ss_changes` からこの残基範囲に収まるものを列挙
  （例: 「残基33 C→H」）
- 領域内の SASA 変化: `sasa_changes.top_decreases` と `top_increases` から
  この領域に収まるものを最大 3 件、残基番号と ΔSASA を添えて列挙
- 領域内の altloc 残基: `altloc_residues.structure_1` と `structure_2` から
  この範囲に収まるものがあれば「この領域には altloc を持つ残基が N 個存在」
  と事実のみ記す（機能的解釈は禁止）

### 4. 配列特筆事項（オプション）

`top_ca_movers` のうち `res_name_1 != res_name_2`（変異）があれば「変位の大きな
残基 N に変異 LEU→VAL」と事実のみ記載。変異がなければこのセクションは省略。

### 5. 警告（条件付き）

`facts.json.warnings` が空でなければ、各警告を1行ずつ列挙:

- `low_sequence_identity_X.XX` → 「配列同一性が X% と低いため、構造比較の解釈に
  注意が必要」
- `multiple_models_detected` → 「複数モデルが検出されたため、第1モデルのみを使用」
- その他の警告はそのまま短く述べる

### 6. 付録: 成果物

`artifacts.aligned_structure` のパスを明記します。

## 執筆スタイル

- 日本語、ですます調
- 各セクション短く（全体で 600 字〜1200 字を目安）
- 見出しは H2 (`##`) レベル
- 数値は `facts.json` の値をそのまま使う（四捨五入は既に施されている）
- 不確かなことは書かない。`facts.json` にないなら書かない。

## 最終チェック（書き終えた後に自分で確認）

- [ ] バックグラウンド知識からの言及が混入していないか
- [ ] 動いていない領域への言及がないか
- [ ] 全ての数値が `facts.json` 由来か
- [ ] 「知られている」「報告されている」「典型的な」等のNGフレーズが無いか
- [ ] 機能的解釈（「〜に関与する」「〜を促進する」）をしていないか
```

- [ ] **Step 2: Commit**

```bash
git add templates/report_prompt.md
git commit -m "docs: add strict report-writing prompt with no-background-knowledge rule"
```

---

## Task 17: `SKILL.md` — Claude Code skill definition

**Files:**
- Create: `SKILL.md`

- [ ] **Step 1: Write `SKILL.md`**

Create `SKILL.md`:
```markdown
---
name: compare-structures
description: Compare two protein structures (apo/holo, open/closed, WT/mutant, etc.) using ChimeraX and explain the conformational change in Japanese. Use when the user provides two PDB IDs or two structure files and asks for a structural comparison or conformational analysis.
allowed-tools: Read, Write, Bash
---

# compare-structures

Compare two protein structures via headless ChimeraX and produce a Japanese
analytical report grounded strictly in computed facts.

## Workflow

1. **Extract inputs from the user request.** Two structures, each either a
   4-character PDB ID (e.g. `1AKE`) or a path to a local `.pdb`/`.cif`/`.mmcif`
   file. If the request is ambiguous, ask the user for clarification before
   proceeding.

2. **Decide an output directory.** Use a timestamp-suffixed name under `runs/`
   in the repo root (or the caller's current working directory if the repo is
   not present):
   ```
   runs/<id1>_vs_<id2>_<YYYYmmdd_HHMMSS>/
   ```

3. **Run the analysis pipeline.** Use `Bash` to invoke `analyze.py` from this
   skill's directory:
   ```bash
   "<skill_dir>/analyze.py" \
     --in1 "<in1>" --in2 "<in2>" \
     --out "<output_dir>"
   ```
   Do not set `--timeout` unless the user asks — the default (30 minutes) is
   intended for most structures.

4. **Check the exit status.**
   - **Exit 0:** continue to step 5.
   - **Non-zero:** read `<output_dir>/error.json` and summarize the failure to
     the user in 2-3 Japanese sentences. Do not continue to step 5. Do not
     paste stack traces into chat — refer the user to the error.json path
     instead.

5. **Read the facts and the prompt.** Use `Read` to load:
   - `<output_dir>/facts.json`
   - `<skill_dir>/templates/report_prompt.md`

6. **Write the report.** Following the prompt in `report_prompt.md` strictly
   (every hard constraint, in particular the no-background-knowledge rule),
   use `Write` to create `<output_dir>/report.md`.

7. **Reply to the user.** 2-5 lines summarizing:
   - The headline metrics (overall RMSD, number of moved regions)
   - Paths to the artifacts (`report.md`, `aligned.cif`, `facts.json`)
   Example:
   > 1AKE と 4AKE の比較が完了しました。全体 Cα RMSD は 5.53 Å、動いた領域は
   > A/30-59 と A/118-167 の 2 箇所。詳細は `runs/1AKE_vs_4AKE_20260409_124530/report.md`
   > を参照してください。

## Hard Constraints

- **No background knowledge in the report.** The prompt in
  `templates/report_prompt.md` forbids literature context, mechanistic
  interpretation, and named-entity priors. Follow it literally.
- **Do not skip the pipeline.** Never write a report without running
  `analyze.py` — the report must reflect the actual `facts.json` for this run.
- **Do not modify `facts.json`.** It is a generated artifact.

## Failure Modes

| Exit code | Meaning | Action |
|---|---|---|
| 0 | Success | Proceed to report writing |
| 2 | Input validation failed | Summarize the validation error to the user |
| 3 | ChimeraX subprocess failed / timed out | Summarize, point at `error.json` |
| 4 | Missing `raw.json` after ChimeraX ran | Report a pipeline bug (rare) |
| 5 | Post-processing failed | Summarize, point at `error.json` |

## Dependencies

- ChimeraX must be installed. The script looks at `$CHIMERAX_PATH` first,
  then the first `chimerax` on `PATH`.
- `uv` must be installed (the `analyze.py` shebang uses
  `#!/usr/bin/env -S uv run --script`).
```

- [ ] **Step 2: Commit**

```bash
git add SKILL.md
git commit -m "feat: add SKILL.md defining the compare-structures skill entry point"
```

---

## Task 18: `docs/manual_review_checklist.md`

**Files:**
- Create: `docs/manual_review_checklist.md`

- [ ] **Step 1: Write the checklist**

Create `docs/manual_review_checklist.md`:
```markdown
# Manual Review Checklist — Generated `report.md`

Automated tests cannot validate the Japanese prose in a generated report
because LLM output is inherently variable. Use this checklist when reviewing
a new sample report during development or when diagnosing a regression.

## 1. Background-knowledge contamination

Search the report for these NG phrases (case-insensitive):

- `known to`, `known as`, `known that`
- `reported`, `has been reported`, `commonly reported`
- `typical`, `typically`, `commonly observed`
- `catalytic`, `active site`, `allosteric`
- `P-loop`, `Rossmann fold`, `Walker motif`
- 「知られている」「報告されている」「典型的な」「一般に」「触媒」「活性中心」
  「既知の」「通常」「よく観察される」

If any appear, the report violates the no-background-knowledge rule. Fix
either the prompt (templates/report_prompt.md) or the execution.

## 2. Numeric agreement with facts.json

For every numeric value in the report, check that the same value appears in
`facts.json`. Specifically verify:

- [ ] Overall RMSD matches `alignment.overall_rmsd_angstrom`
- [ ] Aligned residue count matches `alignment.n_aligned_residues`
- [ ] Sequence identity matches `alignment.sequence_identity`
- [ ] Each moved region's range matches `moved_regions[*].residue_range_label`
- [ ] Each moved region's displacement stats match
- [ ] SASA deltas quoted in the report are present in `sasa_changes`
- [ ] SS changes quoted in the report are present in `ss_changes`

## 3. Stationary-region leakage

- [ ] No residue range or residue number is mentioned that is not inside a
      `moved_regions[*].residue_range` or in `top_ca_movers`
- [ ] No chain is mentioned whose `chain_summary[*].significant_change` is
      `false`

## 4. Adaptive drill-down honored

- [ ] If `drill_down_flags.report_residue_level` is `false`, there is no
      residue-level detail section
- [ ] If `condition == "structures_nearly_identical"`, the report is short
      and says no significant change was detected
- [ ] If `condition == "diffuse_motion"`, this is explicitly stated

## 5. Warnings honored

- [ ] Every warning in `facts.json.warnings` appears in the report (short,
      factual)

## 6. Style

- [ ] All qualitative adjectives are paired with numeric values
- [ ] The report is between 600 and 1200 Japanese characters
- [ ] Tone is analytical, not speculative
```

- [ ] **Step 2: Commit**

```bash
git add docs/manual_review_checklist.md
git commit -m "docs: add manual review checklist for generated reports"
```

---

## Task 19: `README.md`

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write the README**

Create `README.md`:
```markdown
# compare-structures-skill

A Claude Code skill that compares two protein structures via headless
ChimeraX and produces a Japanese analytical report grounded strictly in
computed facts.

Given two PDB IDs (or two structure files), this skill:

1. Superposes the structures using ChimeraX matchmaker.
2. Extracts per-residue Cα displacements, SASA changes, SS changes, and
   altloc information.
3. Clusters contiguous high-displacement residues into moved regions.
4. Writes a `facts.json` with all computed metrics.
5. Generates a Japanese `report.md` that describes only what the analysis
   found — no literature background, no mechanistic interpretation, no
   training-data priors.

## Artifacts per run

```
runs/<id1>_vs_<id2>_<timestamp>/
├── report.md       # Japanese analytical report (user-facing)
├── aligned.cif     # Matchmaker-superposed structures (both models)
├── facts.json      # Fact sheet that Claude reads when writing report.md
└── raw.json        # Raw data dumped by chimerax_script.py (debug aid)
```

## Installation

This skill is designed to live under `~/.claude/skills/compare-structures/`
via Nix + Home Manager (see `~/dotfiles`). For development, clone this repo
and symlink it:

```bash
ln -s /path/to/compare-structures-skill ~/.claude/skills/compare-structures
```

## Requirements

- [ChimeraX](https://www.cgl.ucsf.edu/chimerax/) 1.9 or newer
- [uv](https://docs.astral.sh/uv/) for running `analyze.py`
- Set `CHIMERAX_PATH` if ChimeraX is not on your `PATH`

## Direct CLI usage

```bash
./analyze.py --in1 1AKE --in2 4AKE --out runs/ake
```

## Running tests

Unit and contract tests (no ChimeraX needed):

```bash
uv run --with pytest --with numpy --with jsonschema --with click pytest -v
```

Integration tests (ChimeraX required, opt-in):

```bash
uv run --with pytest --with numpy --with jsonschema --with click pytest -v -m chimerax
```

## Documentation

- [Design spec](docs/superpowers/specs/2026-04-09-compare-structures-design.md)
- [Implementation plan](docs/superpowers/plans/2026-04-09-compare-structures-implementation.md)
- [Manual review checklist](docs/manual_review_checklist.md)
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README"
```

---

## Final Verification

After all tasks complete, run the full unit test suite one more time:

```bash
uv run --with pytest --with numpy --with jsonschema --with click pytest -v
```

Expected: every test in `tests/test_validators.py`, `test_clustering.py`,
`test_metrics.py`, `test_thresholds.py`, `test_errors.py`,
`test_facts_builder.py`, `test_chimerax_runner.py`, and `test_cli.py`
PASSES. Integration tests in `test_integration.py` are skipped unless
ChimeraX is installed.

Then, if ChimeraX is available locally, run the integration suite:

```bash
uv run --with pytest --with numpy --with jsonschema --with click pytest -v -m chimerax
```

Expected: all 3 integration tests PASS.

Finally, try the skill end-to-end manually:

```bash
./analyze.py --in1 1AKE --in2 4AKE --out runs/first-real-run
cat runs/first-real-run/facts.json | head -80
```

Expected: `facts.json` shows overall RMSD in 5-7 Å range and 2+ moved
regions overlapping 118-167 and 30-59.

Review the generated `report.md` against
`docs/manual_review_checklist.md` before considering the skill complete.
