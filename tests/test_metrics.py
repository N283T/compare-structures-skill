"""Tests for compare_structures.metrics."""

import numpy as np
import pytest  # noqa: F401

from compare_structures.metrics import (
    PairedResidue,  # noqa: F401
    displacement,
    kabsch_transform,  # noqa: F401
    pair_residues,
    rmsd,
    rotation_angle_deg,  # noqa: F401
    sasa_deltas,  # noqa: F401
    sequence_identity,
    ss_changes,  # noqa: F401
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
