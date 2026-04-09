"""Tests for compare_structures.facts_builder."""

import json
from pathlib import Path

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
