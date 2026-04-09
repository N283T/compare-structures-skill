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


def kabsch_transform(points_1, points_2):  # noqa: ARG001
    raise NotImplementedError


def rotation_angle_deg(R):  # noqa: ARG001
    raise NotImplementedError
