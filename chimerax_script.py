"""Run inside ChimeraX to open two structures, run matchmaker, extract data,
save aligned.cif, and write raw.json.

Invocation (from chimerax_runner.py):
  chimerax --nogui --exit --silent --script \
    "chimerax_script.py <in1> <in2> <raw_json_out> <aligned_cif_out> <chain1> <chain2>"

Each of <in1>, <in2> is either a 4-character PDB ID or an absolute file path.
<chain1>, <chain2> are chain IDs to restrict matchmaker to, or "" (empty
string) for auto.

The script exits with code 0 on success, non-zero on failure; on failure, a
structured one-line JSON error is printed to stderr so the parent analyze.py
can capture it.
"""

from __future__ import annotations

import json
import sys
import traceback

# The ChimeraX session is provided in the script's global scope as 'session'.
# We rebind it here to satisfy static analyzers — it is set by ChimeraX itself.
session = globals().get("session")  # noqa: F811


def _emit_error(error_type: str, message: str) -> None:
    sys.stderr.write(json.dumps({"error_type": error_type, "message": message}) + "\n")
    sys.stderr.flush()


def _normalize_ss(ss_int: int) -> str:
    # ChimeraX Residue.ss_type: 0=coil/other, 1=helix, 2=strand.
    if ss_int == 1:
        return "H"
    if ss_int == 2:
        return "E"
    return "C"


def _classify_input(arg: str) -> dict:
    import os

    if len(arg) == 4 and arg[0].isdigit() and arg.isalnum():
        return {"id": arg.upper(), "source": "pdb_id"}
    return {"id": os.path.splitext(os.path.basename(arg))[0], "source": "file", "path": arg}


def _open_input(arg: str, classify: dict):
    from chimerax.core.commands import run

    if classify["source"] == "pdb_id":
        return run(session, f"open {classify['id']}")[0]
    return run(session, f"open {classify['path']}")[0]


def _filter_by_chain(model, chain_id: str):
    """Return the atoms of ``model`` restricted to ``chain_id`` (empty string = all)."""
    if not chain_id:
        return model.atoms
    mask = model.atoms.residues.chain_ids == chain_id
    filtered = model.atoms[mask]
    if len(filtered) == 0:
        raise RuntimeError(f"chain {chain_id!r} not found in model")
    return filtered


def _run_matchmaker(model_ref, model_move, chain_ref: str, chain_move: str):
    from chimerax.match_maker.match import cmd_match

    match_atoms = _filter_by_chain(model_move, chain_move)
    ref_atoms = _filter_by_chain(model_ref, chain_ref)
    results = cmd_match(session, match_atoms=match_atoms, to=ref_atoms)
    if not results:
        raise RuntimeError("matchmaker produced no results (structures may be unrelated)")
    return results


def _extract_altloc_info(residue):
    alt_ids: list[str] = []
    max_occ = 0.0
    for atom in residue.atoms:
        occ = float(getattr(atom, "occupancy", 1.0))
        if occ > max_occ:
            max_occ = occ
        alt = getattr(atom, "alt_loc", "")
        if alt and alt not in (" ", "") and alt not in alt_ids:
            alt_ids.append(alt)
    if not alt_ids:
        max_occ = 1.0
    return alt_ids, max_occ


def _collect_residue_data(model, model_idx: int) -> list[dict]:
    # Run measure sasa first so residue.area is populated.
    from chimerax.core.commands import run

    run(session, f"measure sasa #{model_idx}")

    chains_out: dict[str, list[dict]] = {}
    for residue in model.residues:
        principal = residue.principal_atom
        if principal is None:
            continue  # non-polymer or missing Cα
        chain_id = residue.chain_id
        ca = principal.scene_coord  # numpy 3-vector in aligned frame
        alt_ids, max_occ = _extract_altloc_info(residue)
        entry = {
            "chain_id": chain_id,
            "res_num": int(residue.number),
            "res_name": residue.name,
            "ca_coord": [float(ca[0]), float(ca[1]), float(ca[2])],
            "sasa": float(getattr(residue, "area", 0.0)),
            "ss_type": _normalize_ss(int(getattr(residue, "ss_type", 0))),
            "altloc_ids": alt_ids,
            "max_occupancy": float(max_occ),
        }
        chains_out.setdefault(chain_id, []).append(entry)

    return [
        {"chain_id": cid, "model": model_idx, "residues": residues}
        for cid, residues in sorted(chains_out.items())
    ]


def main(argv: list[str]) -> int:
    if len(argv) != 6:
        _emit_error("script_usage", f"expected 6 args, got {len(argv)}: {argv}")
        return 2

    in1, in2, raw_out, aligned_out, chain1, chain2 = argv

    try:
        from chimerax.core.commands import run

        c1 = _classify_input(in1)
        c2 = _classify_input(in2)

        model_1 = _open_input(in1, c1)
        model_2 = _open_input(in2, c2)

        mm_results = _run_matchmaker(
            model_ref=model_1,
            model_move=model_2,
            chain_ref=chain1,
            chain_move=chain2,
        )
        # Aggregate matchmaker stats across all chain-pair matches.
        full_rmsd_weighted_sum = 0.0
        final_rmsd_weighted_sum = 0.0
        n_full_total = 0
        n_final_total = 0
        per_chain = []
        for r in mm_results:
            n_full = len(r["full match atoms"])
            n_final = len(r["final match atoms"])
            full_rmsd_weighted_sum += (float(r["full RMSD"]) ** 2) * n_full
            final_rmsd_weighted_sum += (float(r["final RMSD"]) ** 2) * n_final
            n_full_total += n_full
            n_final_total += n_final
            per_chain.append(
                {
                    "n_full": n_full,
                    "n_final": n_final,
                    "full_rmsd": float(r["full RMSD"]),
                    "final_rmsd": float(r["final RMSD"]),
                }
            )
        full_rmsd = (full_rmsd_weighted_sum / n_full_total) ** 0.5 if n_full_total else 0.0
        final_rmsd = (final_rmsd_weighted_sum / n_final_total) ** 0.5 if n_final_total else 0.0

        # Extract per-residue data AFTER matchmaker so scene_coord is aligned.
        chains_1 = _collect_residue_data(model_1, 1)
        chains_2 = _collect_residue_data(model_2, 2)

        # Save aligned mmCIF with both models.
        run(session, f"save '{aligned_out}' format mmcif models #1,2")

        chimerax_version = "unknown"
        try:
            from chimerax.core import version as _v

            chimerax_version = str(_v)
        except Exception:  # noqa: BLE001
            pass

        raw = {
            "input1": {**c1, "model_id": 1},
            "input2": {**c2, "model_id": 2},
            "matchmaker": {
                "reference_model": 1,
                "moved_model": 2,
                "full_rmsd": float(full_rmsd),
                "final_rmsd": float(final_rmsd),
                "n_full_pairs": int(n_full_total),
                "n_final_pairs": int(n_final_total),
                "per_chain": per_chain,
            },
            "chains": chains_1 + chains_2,
            "chimerax_version": chimerax_version,
            "schema_version": "1.0",
        }
        with open(raw_out, "w") as f:
            json.dump(raw, f, indent=2)
        return 0

    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()
        _emit_error(type(e).__name__, f"{e}\n{tb}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
