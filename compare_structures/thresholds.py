"""Threshold constants and drill-down decision logic."""

from __future__ import annotations

# Thresholds — see design spec §7.
DRILL_DOWN_RMSD_THRESHOLD: float = 2.0  # Å
NEARLY_IDENTICAL_RMSD: float = 0.5  # Å
MIN_MOVED_DISPLACEMENT: float = 3.0  # Å
MIN_REGION_LENGTH: int = 3  # residues
GAP_TOLERANCE: int = 3  # residues
SASA_REPORT_THRESHOLD: float = 30.0  # Å² per residue
SASA_TOTAL_REPORT_THRESHOLD: float = 100.0  # Å² total
LOW_IDENTITY_THRESHOLD: float = 0.30  # fraction
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
            f"overall RMSD {overall_rmsd:.2f} \u00c5 > threshold {DRILL_DOWN_RMSD_THRESHOLD} \u00c5"
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
