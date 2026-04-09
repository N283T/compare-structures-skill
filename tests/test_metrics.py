"""Tests for compare_structures.metrics."""

import numpy as np
import pytest  # noqa: F401

from compare_structures.metrics import (
    PairedResidue,  # noqa: F401
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


class TestSasaDeltas:
    def test_filters_small_changes(self):
        c1 = [
            _make_residue(1, "A", (0, 0, 0), sasa=100.0),
            _make_residue(2, "B", (0, 0, 0), sasa=200.0),
            _make_residue(3, "C", (0, 0, 0), sasa=50.0),
        ]
        c2 = [
            _make_residue(1, "A", (0, 0, 0), sasa=105.0),  # delta +5  (below)
            _make_residue(2, "B", (0, 0, 0), sasa=150.0),  # delta -50 (above)
            _make_residue(3, "C", (0, 0, 0), sasa=90.0),  # delta +40 (above)
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
        c1 = [_make_residue(1, "A", (0, 0, 0), ss="H"), _make_residue(2, "B", (0, 0, 0), ss="H")]
        c2 = [_make_residue(1, "A", (0, 0, 0), ss="H"), _make_residue(2, "B", (0, 0, 0), ss="C")]
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
