"""Tests for compare_structures.thresholds."""

from compare_structures.thresholds import (
    DRILL_DOWN_RMSD_THRESHOLD,
    NEARLY_IDENTICAL_RMSD,
    compute_drill_down_flags,
    detect_soft_condition,
)


class TestComputeDrillDownFlags:
    def test_small_rmsd_no_drill_down(self):
        flags = compute_drill_down_flags(overall_rmsd=0.8, n_moved_regions=0, total_sasa_delta=5.0)
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
        result = detect_soft_condition(overall_rmsd=0.1, n_moved_regions=0)
        assert result == "structures_nearly_identical"

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
