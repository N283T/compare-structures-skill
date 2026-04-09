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
        raise ValueError(f"shape mismatch: {points_1.shape} vs {points_2.shape}")
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
