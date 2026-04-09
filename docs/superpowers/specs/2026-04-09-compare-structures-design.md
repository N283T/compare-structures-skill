# compare-structures Skill — Design

- **Date:** 2026-04-09
- **Status:** Draft, pending user review
- **Working directory:** `/Users/nagaet/explain-conf-skill/` (future repo name: `compare-structures-skill`)
- **Final install location:** `~/dotfiles/claude/.claude/skills/compare-structures/` (after stabilization)

## 1. Overview

A Claude Code skill that, given two protein structures, runs ChimeraX under
the hood to compute the conformational change between them and produces a
Japanese natural-language report grounded strictly in the computed facts.

The primary use case is comparing two snapshots of the same (or homologous)
protein in different states — apo/holo, open/closed, wild-type/mutant — and
getting an analytical summary of what moved and how.

## 2. Goals and Non-Goals

### Goals

- Accept two structures as either PDB IDs or local file paths (mmCIF/PDB).
- Superpose them via ChimeraX matchmaker and compute deterministic,
  reproducible metrics at chain and residue levels.
- Generate a concise Japanese markdown report that adaptively drills down
  from chain-level summary into residue-level detail only where significant
  motion was detected.
- Persist the superposed structure as an `aligned.cif` artifact so users
  can open it later in any molecular viewer.
- Keep report prose strictly grounded in the analysis output of the current
  run — no literature context, no mechanistic priors, no named-entity
  interpretations from training data.

### Non-Goals (MVP)

- Atom-level (side-chain chi angle, hydrogen-bond network) detail. Left as
  Phase 2.
- Automated screenshot / morph-animation generation. Left as Phase 2.
- MD trajectory analysis, NMR ensemble statistics, multi-state comparisons
  beyond two structures.
- Structured JSON output as a user-facing format (internal `facts.json`
  exists, but the user-visible contract is the markdown report).
- LLM-driven biological interpretation or literature citations.

## 3. User Experience

### Invocation

Triggered by natural language such as:

- 「1AKE と 4AKE の構造変化を比較して」
- 「このPDBファイルとあのPDBファイル、open/closedの違いを解析して」

Claude recognizes the intent from the skill's `description` field in the
frontmatter, reads `SKILL.md`, and follows the workflow.

### What the user sees

1. Claude invokes the analysis pipeline via `Bash`.
2. Claude writes a short summary to the chat (2-5 lines), pointing at the
   generated artifacts on disk.
3. The full report lives in `report.md` inside a per-run output directory.

Example chat response:

> 1AKE と 4AKE の比較が完了しました。全体 Cα RMSD は 5.53 Å、動いた領域は
> A/30-59 と A/118-167 の 2 箇所。詳細: `runs/1AKE_vs_4AKE_<ts>/report.md`

### Artifacts (per run)

```
runs/<id1>_vs_<id2>_<timestamp>/
├── report.md       # Japanese analytical report (user-facing)
├── aligned.cif     # Matchmaker-superposed structures (both models)
├── facts.json      # Fact sheet Claude reads when writing report.md
└── raw.json        # Raw data dumped by chimerax_script.py (debug aid)
```

## 4. Architecture

```
User message
      │
      ▼
 Claude (driven by SKILL.md)
      │  Bash
      ▼
 analyze.py  ──────────────────┐
   - input validation          │
   - spawns chimerax subprocess│
   - post-processing           │
                               │ subprocess
                               ▼
                    chimerax --nogui --exit
                    chimerax_script.py
                    (extracts raw data via
                     ChimeraX Python API)
                               │
                               ▼
                    raw.json (intermediate)
                               │
                               ▼
 analyze.py  (reads raw.json)
   - per-residue Cα displacement
   - moved-region clustering
   - SASA / SS diff
   - threshold judgment
   - writes facts.json
      │
      ▼
 Claude
   - Read facts.json
   - Read templates/report_prompt.md
   - Write report.md (Japanese)
   - Reports artifact paths to user
```

### Key separation of concerns

| Responsibility | Owner | Rationale |
|---|---|---|
| ChimeraX invocation and raw-data extraction | `chimerax_script.py` | Runs inside ChimeraX's Python interpreter; touches the ChimeraX API only |
| Numerical analysis, clustering, threshold logic | `analyze.py` | Deterministic, ChimeraX-free, unit-testable on synthetic numpy inputs |
| Natural-language report generation | Claude, guided by `SKILL.md` and `templates/report_prompt.md` | Prose is the LLM's domain; facts are pre-computed and handed in |
| Output quality guardrails (no background knowledge, facts only) | `templates/report_prompt.md` | One place owns the "no literature, no priors" constraint |

## 5. Components

### 5.1 `SKILL.md`

Frontmatter:

```yaml
---
name: compare-structures
description: Compare two protein structures (apo/holo, open/closed, WT/mutant, etc.) using ChimeraX and explain the conformational change in Japanese. Use when the user provides two PDB IDs or two structure files and asks for a structural comparison or conformational analysis.
allowed-tools: Read, Write, Bash
---
```

Body workflow:

1. Extract two inputs (PDB IDs or file paths) from the user request.
2. Decide an output directory under `runs/<id1>_vs_<id2>_<timestamp>/`.
3. Invoke `analyze.py` via `Bash` with the two inputs, output dir, and any
   optional flags (chain override, timeout, etc.).
4. On non-zero exit, read `error.json`, summarize the failure to the user
   in 2-3 Japanese lines, skip report writing.
5. On success, `Read` `facts.json` and `templates/report_prompt.md`.
6. Follow the prompt strictly to draft the Japanese report, and `Write`
   it to `report.md`.
7. Reply to the user with a short summary + artifact paths.

### 5.2 `analyze.py`

- PEP 723 inline metadata, `uv run` shebang, Python 3.12+, deps: `numpy`,
  `jsonschema`, `click`.
- CLI:
  ```
  analyze.py --in1 <id-or-path> --in2 <id-or-path> --out <dir>
             [--chain1 A] [--chain2 A] [--timeout 1800]
  ```
- Default timeout: **1800 seconds (30 min)**, overridable via `--timeout`.
- Responsibilities:
  1. Validate inputs: PDB ID regex `^[A-Za-z0-9]{4}$`, or existing file path.
  2. Verify ChimeraX executable is resolvable (env var `CHIMERAX_PATH` or
     `which chimerax`). Hard-error if missing.
  3. Create the output directory (hard-error if not writable).
  4. Spawn `chimerax --nogui --exit --silent --script
     "<path-to>/chimerax_script.py <args>"` as a subprocess with the
     configured timeout.
  5. On subprocess failure / timeout: write `error.json`, exit non-zero.
  6. Read `raw.json` produced by the subprocess.
  7. Compute per-residue Cα displacements using aligned coordinates from
     both models.
  8. Cluster moved regions (see thresholds, §7).
  9. Compute SASA deltas and SS changes per residue, filter by thresholds.
  10. Determine drill-down flags from overall RMSD and region statistics.
  11. Extract altloc-bearing residues per structure (for the "A" plan — see
      §8) into `altloc_residues`.
  12. Write `facts.json` conforming to `schemas/facts.schema.json`.

### 5.3 `chimerax_script.py`

- Runs inside ChimeraX's own Python interpreter.
- Uses the ChimeraX Python API directly where output parsing would be
  brittle (notably `matchmaker` — using `chimerax.match_maker.match` lets
  us get RMSD and aligned-residue counts as return values instead of
  scraping log strings). Uses `run(session, "...")` only for
  side-effectful operations where it's simpler (`open`, `save`, fetch).
- Exact API surface to be confirmed at implementation time via the
  `reference-chimerax-dev` skill.
- Responsibilities (no numpy clustering here — keep it pure extraction):
  1. Open both inputs (PDB ID fetch or local file).
  2. Run matchmaker, align structure 2 onto structure 1.
  3. Extract per-residue data for both models: residue number, residue
     name, chain id, Cα coordinate (in the aligned frame), `area` (SASA
     after running `measure sasa`), `ss_type`, and altloc IDs if present.
  4. Normalize `ss_type` to the `H`/`E`/`C` three-class encoding.
  5. Save the superposed structures as `aligned.cif` (both models).
  6. Dump all extracted data to `raw.json`.
  7. On ChimeraX exceptions, print a structured error line to stderr and
     exit non-zero (the parent `analyze.py` catches this).

### 5.4 `templates/report_prompt.md`

The prompt Claude follows when turning `facts.json` into `report.md`.
Contains:

- **Hard constraints (prohibited):**
  - Literature references or citations.
  - "It is known", "has been reported", "commonly observed" and similar
    priors.
  - Named-entity interpretations ("this is the P-loop", "the catalytic
    lysine").
  - Functional interpretation not supported by the numbers in `facts.json`.
  - Discussion of residues or regions that did not show significant change.
- **Allowed content:**
  - Values present in `facts.json` — RMSDs, residue IDs, displacements,
    SASA deltas, SS changes, rotation angles, hinge-candidate residues,
    altloc residue lists.
  - Neutral Japanese paraphrasing and organization of those values.
- **Output structure of `report.md`:**
  1. Heading: the two input identifiers and the date.
  2. Chain-level summary: overall RMSD, aligned-residue count, number of
     moved regions, one-line headline.
  3. Moved-region detail (only when `drill_down_flags.report_residue_level`
     is true and at least one region exists): per region, range,
     mean/max displacement, rotation and translation (from a Kabsch fit
     of the region-specific Cα subset between the two structures in the
     matchmaker-aligned frame; omitted if fewer than 3 non-collinear
     residues make the fit ill-defined), SS changes within the region,
     SASA changes within the region, any altloc residues within the
     region.
  4. Warnings, if any (from `facts.json.warnings`).
  5. Appendix: artifact file paths.
- **Style constraints:** concise, fact-dense; avoid vague adjectives;
  always pair qualitative words ("大きな", "小さな") with numeric values.

### 5.5 `schemas/`

JSON Schema definitions committed alongside the code so that field
additions are visible in diffs and contract tests can run without ChimeraX.

- `schemas/raw.schema.json`
- `schemas/facts.schema.json`
- `schemas/error.schema.json`

### 5.6 `tests/`

See §9 for the full strategy. Files:

- `tests/test_analyze.py` — unit tests for clustering, thresholds, SASA /
  SS filters, altloc extraction, schema validation.
- `tests/test_integration.py` — end-to-end runs marked
  `@pytest.mark.chimerax`, opt-in.
- `tests/test_schemas.py` — contract tests.
- `tests/fixtures/` — expected value ranges for known pairs.

### 5.7 `docs/`

- `docs/manual_review_checklist.md` — checklist used when reviewing
  generated Japanese reports (see §9).
- `docs/superpowers/specs/2026-04-09-compare-structures-design.md` — this
  document.

## 6. Data Flow and Schemas

### 6.1 `raw.json` (chimerax_script.py → analyze.py)

```json
{
  "input1": {"id": "1AKE", "source": "pdb_id", "model_id": 1},
  "input2": {"id": "4AKE", "source": "pdb_id", "model_id": 2},
  "matchmaker": {
    "reference_model": 1,
    "moved_model": 2,
    "rmsd": 5.53,
    "n_aligned": 208,
    "sequence_identity": 1.0,
    "per_chain": [
      {"ref_chain": "A", "moved_chain": "A", "rmsd": 5.53, "n_aligned": 208}
    ]
  },
  "chains": [
    {
      "chain_id": "A",
      "model": 1,
      "residues": [
        {
          "res_num": 1,
          "res_name": "MET",
          "ca_coord": [x, y, z],
          "sasa": 123.4,
          "ss_type": "H",
          "altloc_ids": []
        }
      ]
    }
  ],
  "chimerax_version": "1.x.y",
  "schema_version": "1.0"
}
```

Residue data is recorded for both models in the superposed (post-matchmaker)
coordinate frame, so residue-wise subtraction yields true displacement.

### 6.2 `facts.json` (analyze.py → Claude)

```json
{
  "inputs": {
    "structure_1": {"id": "1AKE", "source": "pdb_id"},
    "structure_2": {"id": "4AKE", "source": "pdb_id"}
  },
  "alignment": {
    "method": "matchmaker",
    "reference": "1AKE",
    "moved": "4AKE",
    "overall_rmsd_angstrom": 5.53,
    "n_aligned_residues": 208,
    "sequence_identity": 1.0
  },
  "chain_summary": [
    {
      "chain_id": "A",
      "n_residues": 214,
      "ca_displacement_stats": {
        "mean": 2.8, "median": 1.1, "max": 18.4, "p95": 12.2
      },
      "significant_change": true
    }
  ],
  "moved_regions": [
    {
      "chain_id": "A",
      "residue_range": [30, 59],
      "residue_range_label": "A/30-59",
      "n_residues": 30,
      "mean_ca_displacement": 8.2,
      "max_ca_displacement": 14.1,
      "estimated_rotation_deg": 28.5,
      "estimated_translation_angstrom": 3.2,
      "hinge_candidate_residues": [29, 60]
    }
  ],
  "top_ca_movers": [
    {"chain_id": "A", "res_num": 42, "res_name": "LEU", "displacement": 14.1}
  ],
  "sasa_changes": {
    "total_delta_angstrom2": -450.3,
    "top_decreases": [
      {"chain_id": "A", "res_num": 42, "res_name": "LEU", "delta_sasa": -88.2}
    ],
    "top_increases": []
  },
  "ss_changes": [
    {"chain_id": "A", "res_num": 33, "res_name": "VAL", "ss_before": "C", "ss_after": "H"}
  ],
  "altloc_residues": {
    "structure_1": [
      {"chain_id": "A", "res_num": 42, "res_name": "LEU",
       "altloc_ids": ["A", "B"], "max_occupancy": 0.6}
    ],
    "structure_2": []
  },
  "drill_down_flags": {
    "report_residue_level": true,
    "report_sasa": true,
    "report_ss_changes": true,
    "reasons": {
      "report_residue_level": "overall RMSD 5.53 Å > threshold 2.0 Å",
      "report_sasa": "|total ΔSASA| 450 > threshold 100"
    }
  },
  "warnings": [],
  "condition": null,
  "artifacts": {
    "aligned_structure": "aligned.cif"
  },
  "meta": {
    "schema_version": "1.0",
    "chimerax_version": "1.x.y",
    "generated_at": "2026-04-09T12:34:56Z"
  }
}
```

### 6.3 `error.json` (on hard failure)

```json
{
  "error_type": "chimerax_fetch_failed",
  "message": "failed to fetch pdb id '9ZZZ': not found",
  "stage": "chimerax_script",
  "stderr_tail": "... last 2000 chars ...",
  "schema_version": "1.0"
}
```

## 7. Thresholds and Defaults

All thresholds live as named constants in `analyze.py` and are also written
verbatim into `facts.json.drill_down_flags.reasons` so reports can reference
them.

| Judgment | Default | Rationale |
|---|---|---|
| Drill-down trigger (chain level) | overall RMSD > 2.0 Å | Below this, crystal-form differences and coordinate noise dominate |
| Moved-residue cutoff | Cα displacement > 3.0 Å, ≥3 consecutive residues | Suppresses per-residue thermal jitter |
| Moved-region merge | gap ≤ 3 residues → merge | Keeps short stable runs inside one logical region |
| SASA reporting | \|ΔSASA\| > 30 Å² | Filters noise |
| SS reporting | every change after H/E/C normalization | Typically few, worth listing in full |
| Nearly-identical flag | overall RMSD < 0.5 Å | Triggers a shortened report |
| Low sequence-identity warning | < 30% | Flags homology-stretch comparisons |
| Subprocess timeout | 1800 s (overridable via `--timeout`) | Accommodates large assemblies |

## 8. Error Handling and Edge Cases

### 8.1 Three-tier classification

| Tier | Meaning | Artifact | Exit |
|---|---|---|---|
| Hard error | Analysis cannot proceed | `error.json` only | non-zero |
| Soft condition | Analysis succeeded in a special mode | `facts.json` with `condition` | zero |
| Warning | Analysis succeeded, note-worthy fact | `facts.json.warnings[]` | zero |

### 8.2 Hard errors

- Invalid PDB ID format
- PDB ID fetch failure (not found / network)
- File-not-found or unsupported format for local path
- ChimeraX executable not resolvable
- ChimeraX subprocess crash / non-zero exit
- ChimeraX subprocess timeout
- Matchmaker produces zero aligned residues
- Output directory not writable

### 8.3 Soft conditions (not errors)

- `structures_nearly_identical` — overall RMSD < 0.5 Å. Report is shortened
  to "no significant change detected"; residue-level sections are omitted.
- `report_residue_level == false` — overall RMSD between 0.5 Å and the
  drill-down threshold. Chain-level report only.
- `diffuse_motion` — overall RMSD above threshold but no continuous region
  clears the moved-region filter. Report states this explicitly.

### 8.4 Warnings

- Chain count mismatch between the two inputs
- Multi-model file detected (first model used, others ignored)
- Missing residues > 10% in either structure
- Non-standard residues present
- Sequence identity < 30%

### 8.5 altloc handling

Alternative locations carry intrinsic conformational information, so they
are preserved as facts without complicating the main comparison pipeline:

- `chimerax_script.py` extracts residues bearing altlocs (IDs and maximum
  occupancy) into `raw.json`.
- `analyze.py` copies this into `facts.json.altloc_residues`, split by
  structure.
- Comparison math uses ChimeraX's default altloc selection (typically
  highest-occupancy). No multi-altloc expansion in MVP.
- The report mentions altloc-bearing residues **only when they fall inside
  a reported moved region**, to avoid flooding the prose. The mention is
  purely factual ("この領域には altloc を持つ残基が N 個存在") with no
  interpretation.

### 8.6 Chain selection policy

1. Prefer chain IDs present in both structures (e.g., `A` vs `A`).
2. Otherwise pair the longest protein chain in each.
3. Otherwise let matchmaker pick and record the choice in
   `facts.json.alignment.per_chain`.
4. `--chain1` and `--chain2` CLI overrides exist from day one.

## 9. Testing Strategy

### 9.1 Three layers

| Layer | Target | Needs ChimeraX | Speed |
|---|---|---|---|
| Unit | Pure Python logic in `analyze.py` | No | Seconds |
| Contract | JSON Schema conformance | No | Seconds |
| Integration | `chimerax_script.py` + `analyze.py` end-to-end | Yes | Tens of seconds |

### 9.2 Unit tests

Synthetic numpy input drives `analyze.py` logic in isolation. Cases:

- `test_cluster_moved_regions` — displacement profiles produce the
  expected regions, honouring minimum length and gap merging.
- `test_drill_down_threshold` — RMSD + stats map to the correct
  `drill_down_flags`.
- `test_sasa_delta_filter` — only entries with |ΔSASA| above threshold
  are reported.
- `test_ss_change_detection` — only changed residues appear in
  `ss_changes`.
- `test_altloc_extraction` — altloc metadata makes it into `facts.json`
  correctly.
- `test_soft_condition_nearly_identical` — RMSD 0.1 Å triggers the flag.
- `test_facts_json_schema_validation` — generated JSON validates.

### 9.3 Integration tests

Marked `@pytest.mark.chimerax` and skipped when ChimeraX is not resolvable.

- `test_1ake_vs_4ake` — adenylate kinase open/closed.
  - Exit zero.
  - `alignment.overall_rmsd_angstrom` between 5.0 Å and 7.0 Å.
  - `alignment.n_aligned_residues` between 200 and 220.
  - `len(moved_regions) >= 2`.
  - At least one moved region overlaps 118-167 (±3 residues).
  - At least one moved region overlaps 30-59 (±3 residues).
  - `drill_down_flags.report_residue_level` true.
  - `aligned.cif` exists and contains two models.
- `test_identical_structure_pair` — same PDB ID twice.
  - `condition == "structures_nearly_identical"`.
  - `moved_regions` empty.
- `test_invalid_pdb_id` — fake ID `9ZZZ`.
  - Non-zero exit.
  - `error.json` present with `error_type == "chimerax_fetch_failed"`.

Range-based assertions tolerate minor ChimeraX version drift while still
detecting regressions.

### 9.4 Contract tests

Validate `raw.json`, `facts.json`, and `error.json` generated by both unit
and integration tests against their JSON Schemas in `schemas/`.

### 9.5 Not tested automatically

- Japanese prose content of `report.md`. LLM output is inherently
  variable. A manual checklist in `docs/manual_review_checklist.md`
  covers:
  - Background-knowledge contamination (grep for NG phrases such as
    "known to", "catalytic", "reported").
  - Numeric agreement with `facts.json`.
  - No references to residues outside the moved regions.
- ChimeraX itself is trusted.

### 9.6 CI policy

| Layer | CI | Local |
|---|---|---|
| Unit | Yes (GitHub Actions, uv + pytest) | Yes |
| Contract | Yes (GitHub Actions) | Yes |
| Integration | Opt-in (`-m chimerax`) | Yes — required before PR |

ChimeraX is too large for the free GitHub runner. Integration runs live
locally during development; self-hosted runners are a future option.

## 10. Out of Scope / Phase 2

- Atom-level side-chain and hydrogen-bond change reporting.
- Automated screenshot / morph animation artifacts.
- Long-lived MCP session mode (reusing a running ChimeraX across many
  comparisons).
- Multi-altloc expansion (case C of §8.5).
- MD trajectory or NMR ensemble variants.
- English-language report mode.
- Structured JSON as a user-facing output format.

## 11. Open Questions

None at design time. Any open points surfaced during implementation go
into the implementation plan that follows this spec.
