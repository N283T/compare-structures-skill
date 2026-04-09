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
                p for p in paired if region.residue_range[0] <= p.res_num <= region.residue_range[1]
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
    order = np.argsort(-all_disps)[:10] if all_disps.size else np.zeros(0, dtype=int)
    top_movers = [
        {
            "chain_id": all_paired[i].chain_id,
            "res_num": all_paired[i].res_num,
            "res_name": all_paired[i].res_name_1,
            "displacement": round(float(all_disps[i]), 3),
        }
        for i in order
    ]

    drill_flags = compute_drill_down_flags(overall_rmsd, len(moved_regions_all), total_delta)
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
