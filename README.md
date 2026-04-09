# compare-structures-skill

A Claude Code skill that compares two protein structures via headless
ChimeraX and produces a Japanese analytical report grounded strictly in
computed facts.

Given two PDB IDs (or two structure files), this skill:

1. Superposes the structures using ChimeraX matchmaker.
2. Extracts per-residue Cα displacements, SASA changes, SS changes, and
   altloc information.
3. Clusters contiguous high-displacement residues into moved regions.
4. Writes a `facts.json` with all computed metrics.
5. Generates a Japanese `report.md` that describes only what the analysis
   found — no literature background, no mechanistic interpretation, no
   training-data priors.

## Artifacts per run

```
runs/<id1>_vs_<id2>_<timestamp>/
├── report.md       # Japanese analytical report (user-facing)
├── aligned.cif     # Matchmaker-superposed structures (both models)
├── facts.json      # Fact sheet that Claude reads when writing report.md
└── raw.json        # Raw data dumped by chimerax_script.py (debug aid)
```

## Installation

This skill is designed to live under `~/.claude/skills/compare-structures/`
via Nix + Home Manager (see `~/dotfiles`). For development, clone this repo
and symlink it:

```bash
ln -s /path/to/compare-structures-skill ~/.claude/skills/compare-structures
```

## Requirements

- [ChimeraX](https://www.cgl.ucsf.edu/chimerax/) 1.9 or newer
- [uv](https://docs.astral.sh/uv/) for running `analyze.py`
- Set `CHIMERAX_PATH` if ChimeraX is not on your `PATH`

## Direct CLI usage

```bash
./analyze.py --in1 1AKE --in2 4AKE --out runs/ake
```

## Example output

A reference run of the canonical adenylate kinase open/closed pair is
committed under [`examples/1ake_vs_4ake/`](examples/1ake_vs_4ake/). It
includes the four artifacts of a real analysis:

- [`report.md`](examples/1ake_vs_4ake/report.md) — Japanese analytical report
- [`facts.json`](examples/1ake_vs_4ake/facts.json) — computed fact sheet
- `aligned.cif` — matchmaker-superposed structures (two models)
- `raw.json` — raw ChimeraX extraction

The report identifies two moved regions (A/32-70 and A/117-166) with
overall Cα RMSD ≈ 8.24 Å, corresponding to the NMP-binding and LID domain
motions of *E. coli* adenylate kinase — without naming those domains, per
the skill's strict no-background-knowledge rule.

## Running tests

Unit and contract tests (no ChimeraX needed):

```bash
uv run --with pytest --with numpy --with jsonschema --with click pytest -v
```

Integration tests (ChimeraX required, opt-in):

```bash
uv run --with pytest --with numpy --with jsonschema --with click pytest -v -m chimerax
```

## Documentation

- [Design spec](docs/superpowers/specs/2026-04-09-compare-structures-design.md)
- [Implementation plan](docs/superpowers/plans/2026-04-09-compare-structures-implementation.md)
- [Manual review checklist](docs/manual_review_checklist.md)
