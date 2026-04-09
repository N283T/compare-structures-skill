"""Integration tests — require a working ChimeraX installation.

Run locally before pushing:
  uv run --with pytest --with numpy --with jsonschema --with click \
      pytest tests/test_integration.py -v -m chimerax

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
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_REPO_ROOT)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from compare_structures.cli import main; import sys; "
            "sys.exit(main(sys.argv[1:], standalone_mode=False))",
            "--in1",
            in1,
            "--in2",
            in2,
            "--out",
            str(out),
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

    labels = [r["residue_range_label"] for r in facts["moved_regions"]]
    assert any(overlaps(r, 118, 167) for r in facts["moved_regions"]), (
        f"no region overlaps LID 118-167: {labels}"
    )

    # NMP-binding domain (30-59) should overlap at least one moved region.
    assert any(overlaps(r, 30, 59) for r in facts["moved_regions"]), (
        f"no region overlaps NMP 30-59: {labels}"
    )

    # aligned.cif exists and is non-trivial.
    aligned = out / "aligned.cif"
    assert aligned.is_file()
    assert aligned.stat().st_size > 1000  # rough sanity


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
