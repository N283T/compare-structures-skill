"""Cluster residues with high Cα displacement into contiguous moved regions."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MovedRegion:
    chain_id: str
    residue_range: tuple[int, int]  # inclusive [start, end] in residue numbers
    n_residues: int
    mean_displacement: float
    max_displacement: float


def cluster_moved_regions(
    chain_id: str,
    residues: list[int],
    displacements: np.ndarray,
    *,
    min_displacement: float,
    min_length: int,
    gap_tolerance: int,
) -> list[MovedRegion]:
    """Cluster contiguous high-displacement residues into moved regions.

    Parameters
    ----------
    chain_id : str
        Chain identifier stored on every returned region.
    residues : list[int]
        Residue numbers, in ascending order. May contain gaps (missing residues).
    displacements : np.ndarray
        Per-residue Cα displacement in Å, same length as ``residues``.
    min_displacement : float
        A residue is "high" if its displacement strictly exceeds this threshold.
    min_length : int
        Final regions with fewer than this many residues are dropped.
    gap_tolerance : int
        Two high-runs separated by at most this many low residues (by residue number,
        not index) are merged into a single region.
    """
    if len(residues) != len(displacements):
        raise ValueError(
            f"residues and displacements length mismatch: {len(residues)} vs {len(displacements)}"
        )
    if len(residues) == 0:
        return []

    high = displacements > min_displacement

    # Contiguous runs of high residues by index.
    runs: list[tuple[int, int]] = []
    i = 0
    n = len(high)
    while i < n:
        if not high[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and high[j + 1]:
            j += 1
        runs.append((i, j))
        i = j + 1

    # Merge runs whose residue-number gap is within tolerance.
    merged: list[list[int]] = []
    for start, end in runs:
        if merged:
            prev_end = merged[-1][1]
            residue_gap = residues[start] - residues[prev_end] - 1
            if residue_gap <= gap_tolerance:
                merged[-1][1] = end
                continue
        merged.append([start, end])

    # Build MovedRegion objects, filtering by length.
    result: list[MovedRegion] = []
    for start, end in merged:
        n_res = end - start + 1
        if n_res < min_length:
            continue
        slice_ = displacements[start : end + 1]
        result.append(
            MovedRegion(
                chain_id=chain_id,
                residue_range=(int(residues[start]), int(residues[end])),
                n_residues=n_res,
                mean_displacement=float(slice_.mean()),
                max_displacement=float(slice_.max()),
            )
        )
    return result
