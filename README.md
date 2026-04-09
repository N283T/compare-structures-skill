# compare-structures-skill

A Claude Code skill that compares two protein structures via headless
ChimeraX and produces a rich English analytical report grounded in
run-derived facts and togomcp-fetched database context, plus a short
Japanese chat summary returned to the user.

Given two PDB IDs (or two structure files), this skill:

1. Superposes the structures using ChimeraX matchmaker.
2. Extracts per-residue Cα displacements, SASA changes, SS changes, and
   altloc information.
3. Clusters contiguous high-displacement residues into moved regions.
4. Writes a `facts.json` with all computed metrics.
5. Fetches structural metadata (PDB titles, UniProt accessions, protein
   names, organisms, function, keywords, domains) via togomcp and
   persists it to `external_metadata.json`.
6. Generates a rich English `report.md` that interleaves tables,
   paragraphs, and bullets. All run-derived numbers must trace to
   `facts.json`; all DB-derived facts carry provenance markers (`per
   RCSB`, `per UniProt ...`, `per togomcp ...`). Training-data
   background is allowed but must be marked `(general background)` and
   tied to a specific run feature.
7. Replies to the user in Japanese (2–5 lines) summarizing headline
   metrics and artifact paths.

## Artifacts per run

```
runs/<id1>_vs_<id2>_<timestamp>/
├── report.md               # Rich English analytical report (user-facing)
├── aligned.cif             # Matchmaker-superposed structures (both models)
├── facts.json              # Fact sheet that Claude reads when writing report.md
├── external_metadata.json  # togomcp-fetched PDB/UniProt metadata (schema-validated)
└── raw.json                # Raw data dumped by chimerax_script.py (debug aid)
```

## Installation

Claude Code looks up skills under `~/.claude/skills/<skill-name>/`. To
install this skill, make its repo contents available at
`~/.claude/skills/compare-structures/` by any method you prefer:

```bash
# Option A: clone directly
git clone https://github.com/N283T/compare-structures-skill ~/.claude/skills/compare-structures

# Option B: clone anywhere, then symlink
git clone https://github.com/N283T/compare-structures-skill /path/to/compare-structures-skill
ln -s /path/to/compare-structures-skill ~/.claude/skills/compare-structures
```

## Requirements

- [ChimeraX](https://www.cgl.ucsf.edu/chimerax/) 1.9 or newer
- [uv](https://docs.astral.sh/uv/) for running `analyze.py`
- Set `CHIMERAX_PATH` if ChimeraX is not on your `PATH`
- [togomcp](https://github.com/dbcls/togomcp) registered as an MCP
  server in Claude Code. The skill fetches PDB titles, UniProt
  accessions, protein names, organisms, and SPARQL-derived
  function/domain data through togomcp's `list_databases`,
  `search_pdb_entity`, `togoid_convertId`, `search_uniprot_entity`,
  `get_MIE_file`, and `run_sparql` tools. Three install options:
  - Hosted server at <https://togomcp.rdfportal.org/> — no install.
  - `git clone https://github.com/dbcls/togomcp && cd togomcp && uv tool install .`
    — installs `togo-mcp-local` as a uv tool on your `PATH`.
  - `git clone https://github.com/dbcls/togomcp && cd togomcp && uv sync`
    — run via `uv --directory /path/to/togomcp run togo-mcp-local`.

  Local modes additionally require an `NCBI_API_KEY`. See the togomcp
  README for the exact MCP server config.

## Direct CLI usage

```bash
./analyze.py --in1 1AKE --in2 4AKE --out runs/ake
```

## Example output

A reference run of the canonical adenylate kinase open/closed pair is
committed under [`examples/1ake_vs_4ake/`](examples/1ake_vs_4ake/). It
includes the five artifacts of a real analysis:

- [`report.md`](examples/1ake_vs_4ake/report.md) — rich English analytical report
- [`facts.json`](examples/1ake_vs_4ake/facts.json) — computed fact sheet
- [`external_metadata.json`](examples/1ake_vs_4ake/external_metadata.json) — togomcp-fetched PDB/UniProt metadata
- `aligned.cif` — matchmaker-superposed structures (two models)
- `raw.json` — raw ChimeraX extraction

The report identifies two moved regions (A/32–70 and A/117–166) with
overall Cα RMSD ≈ 8.24 Å over 214 aligned residues. Both structures
map to UniProt P69441 (*E. coli* adenylate kinase), so the report names
the CORE / NMPbind / LID three-domain architecture with `per UniProt`
provenance — run-derived numbers and DB-derived context are kept
visually separable via provenance markers.

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

- [Manual review checklist](docs/manual_review_checklist.md)
