"""Tests for compare_structures.clustering."""

import numpy as np

from compare_structures.clustering import MovedRegion, cluster_moved_regions  # noqa: F401


class TestClusterMovedRegions:
    def test_single_contiguous_region(self):
        residues = [10, 11, 12, 13, 14, 15]
        disps = np.array([0.1, 4.0, 5.0, 4.5, 3.5, 0.2])
        regions = cluster_moved_regions(
            "A", residues, disps, min_displacement=3.0, min_length=3, gap_tolerance=3
        )
        assert len(regions) == 1
        r = regions[0]
        assert r.chain_id == "A"
        assert r.residue_range == (11, 14)
        assert r.n_residues == 4
        assert r.max_displacement == 5.0

    def test_two_distinct_regions_no_merge(self):
        residues = list(range(1, 21))
        disps = np.zeros(20)
        disps[2:6] = 4.0  # residues 3-6 (indices 2-5)
        disps[12:16] = 4.5  # residues 13-16 (indices 12-15)
        regions = cluster_moved_regions(
            "A", residues, disps, min_displacement=3.0, min_length=3, gap_tolerance=3
        )
        assert len(regions) == 2
        assert regions[0].residue_range == (3, 6)
        assert regions[1].residue_range == (13, 16)

    def test_merge_across_small_gap(self):
        residues = list(range(1, 21))
        disps = np.zeros(20)
        disps[2:6] = 4.0  # residues 3-6
        disps[8:12] = 4.0  # residues 9-12
        # gap between end (6) and start (9) is residues 7,8 => 2 residues, <= gap_tolerance=3
        regions = cluster_moved_regions(
            "A", residues, disps, min_displacement=3.0, min_length=3, gap_tolerance=3
        )
        assert len(regions) == 1
        assert regions[0].residue_range == (3, 12)

    def test_gap_too_large_keeps_regions_split(self):
        residues = list(range(1, 21))
        disps = np.zeros(20)
        disps[2:6] = 4.0
        disps[12:16] = 4.0
        # gap is residues 7..12 => 5 residues, > gap_tolerance=3
        regions = cluster_moved_regions(
            "A", residues, disps, min_displacement=3.0, min_length=3, gap_tolerance=3
        )
        assert len(regions) == 2

    def test_below_min_length_dropped(self):
        residues = list(range(1, 11))
        disps = np.zeros(10)
        disps[3:5] = 4.0  # only 2 residues — below min_length=3
        regions = cluster_moved_regions(
            "A", residues, disps, min_displacement=3.0, min_length=3, gap_tolerance=3
        )
        assert regions == []

    def test_all_below_threshold_returns_empty(self):
        residues = list(range(1, 11))
        disps = np.full(10, 1.0)
        regions = cluster_moved_regions(
            "A", residues, disps, min_displacement=3.0, min_length=3, gap_tolerance=3
        )
        assert regions == []

    def test_length_mismatch_raises(self):
        import pytest

        with pytest.raises(ValueError, match="length mismatch"):
            cluster_moved_regions(
                "A",
                [1, 2, 3],
                np.array([1.0, 2.0]),
                min_displacement=3.0,
                min_length=3,
                gap_tolerance=3,
            )

    def test_moved_region_statistics(self):
        residues = [10, 11, 12, 13, 14]
        disps = np.array([4.0, 5.0, 6.0, 5.0, 4.0])
        regions = cluster_moved_regions(
            "B", residues, disps, min_displacement=3.0, min_length=3, gap_tolerance=3
        )
        assert len(regions) == 1
        r = regions[0]
        assert r.chain_id == "B"
        assert r.residue_range == (10, 14)
        assert r.n_residues == 5
        assert abs(r.mean_displacement - 4.8) < 1e-9
        assert r.max_displacement == 6.0
