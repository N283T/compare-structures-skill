# compare-structures Rich Report Redesign — Design

- **Date:** 2026-04-09
- **Status:** Draft, pending user review
- **Working directory:** `/Users/nagaet/explain-conf-skill/`
- **Supersedes:** The report-authoring portion of `2026-04-09-compare-structures-design.md`. The original spec's analysis-pipeline design (ChimeraX runner, facts builder, validators, error codes) remains in force.

## 1. Motivation

The original compare-structures skill produced a Japanese report that was, in practice, a bullet-point transcription of `facts.json` fields. When the user exercised the skill end-to-end, the output was criticized as "thin and hard to read" with these specific problems:

- Every section collapsed into bullet lists; no mix of tables, paragraphs, and lists
- No background or structural context — the previous design forbade it outright
- No synthesis across regions or across fact categories (SS + SASA + displacements never correlated in prose)
- Japanese generation visibly compressed technical vocabulary and shortened sentences
- The report added almost no value over the raw `facts.json`

The user explicitly walked back the earlier "no background knowledge" instruction (recorded in `~/.claude/projects/-Users-nagaet-explain-conf-skill/memory/feedback_scientific_reports_rich_format.md`, 2026-04-09) and asked for a redesign that leverages Claude's full capability: rich, expert-level, well-formatted, substantive reports that fuse run-derived facts with structural-biology context.

## 2. Goals and Non-Goals

### Goals

- Produce an expert-level, rich, table-first English report (`report.md`) that combines:
  - All relevant `facts.json` content surfaced in scannable tables
  - DB-derived metadata from `togomcp` (PDB titles, UniProt mapping, protein identity, function annotations)
  - Training-data background on the protein architecture and dynamics, clearly marked as such
  - Synthesis prose that ties motion observations to structural context
- Persist the DB fetch result as a new artifact `external_metadata.json` for reproducibility and debugging.
- Strict provenance marking: every DB-derived fact and every background claim carries an explicit source marker so the reader can trace any statement to its origin.
- Graceful degradation when `togomcp` calls fail: the report is still produced, using training-data context only, and flags the degradation in Section 4 and Section 9.
- Keep the `analyze.py` pipeline and `facts.json` schema completely unchanged (zero Python-side changes).

### Non-Goals

- No changes to `analyze.py`, `chimerax_script.py`, `compare_structures/*.py`, `schemas/facts.schema.json`, or any existing test.
- No changes to the skill's CLI surface or invocation contract.
- No literature citations (author-year references are forbidden).
- No optimization of `togomcp` call budget beyond the usage-guide limits (≤2 SPARQL calls total, pivot on 2 consecutive failures).
- No automated language-quality evaluation. Report quality is validated by manual review plus structural snapshot tests.

## 3. Decisions Record

These were settled during the brainstorming session on 2026-04-09.

| # | Decision | Choice | Rationale |
|---|---|---|---|
| Q1 | Where does DB metadata come from? | **B**: Claude calls `togomcp` at report-generation time; `analyze.py` unchanged | Keeps the analysis pipeline independent of MCP servers and network. `external_metadata.json` is persisted separately so the report is still reproducible given both artifacts. |
| Q2 | Target reader and depth | **A**: structural-biology expert, dense and technical, named entities used without definitions | Matches the actual user. "Aim for depth" is the brief, not length. |
| Q2-rev | Length cap | **No cap**; soft guidance only | Strict numeric caps distort output. Length should fall out of content. Recorded as general feedback memory. |
| Q3 | Background policy | **B**: DB hard facts + training-data protein context, with provenance markers everywhere | Rich reports without verifiable provenance drift into fiction; rich reports without background are thin. Both together, with explicit marking, is the productive path. |
| Q4 | `togomcp` fetch set | **C (Rich)**: `list_databases`, `search_pdb_entity ×2`, `togoid_convertId`, `search_uniprot_entity`, `get_MIE_file(uniprot)`, `run_sparql` on UniProt for function/keywords/domains | Claim the full "expert" brief; keeps the call budget within the togomcp usage guide's 6–15 tool target. |
| Q5 | Condition handling | **B**: all conditions (`drill-down`, `nearly_identical`, `diffuse_motion`) get the full fetch workflow and a rich report, with section coverage (not length caps) scaled by condition | The "no significant change" case is still scientifically informative (mutation? solution condition? crystal form?) and deserves the same depth of context. |
| Shape | Report shape | **Shape 2**: table-first, short interpretive paragraphs between tables, single synthesis paragraph in Section 8 | Scannability plus a clear place for integrated interpretation. Tables handle parallel data (metrics, region comparison, residue listings); prose handles synthesis. |

## 4. Architecture and Data Flow

### 4.1 What changes and what does not

**Unchanged (all of these stay exactly as they are):**

- `analyze.py` entry point and CLI
- `compare_structures/` package (all Python modules)
- `chimerax_script.py`
- `schemas/facts.schema.json`
- `schemas/raw.schema.json`
- `schemas/error.schema.json`
- All existing tests under `tests/`
- `facts.json`, `aligned.cif`, `raw.json` output artifacts
- Error codes (exit 0/2/3/4/5)

**Rewritten:**

- `templates/report_prompt.md` — full rewrite (new structure, English, provenance markers, togomcp integration instructions)
- `SKILL.md` — workflow steps 5–8 rewritten, hard constraints rewritten, `allowed-tools` frontmatter updated
- `docs/manual_review_checklist.md` — full rewrite. The existing file enforces the old no-background-knowledge rule and Japanese length constraint, both of which the new design explicitly reverses. The new checklist covers rich-format structural invariants, provenance-marker presence, graceful-degradation checks, and condition-variant checks.

**Added:**

- `schemas/external_metadata.schema.json` — schema for the new artifact
- `examples/1ake_vs_4ake/external_metadata.json` — regenerated example
- `examples/1ake_vs_4ake/report.md` — regenerated in new format, English
- `tests/test_external_metadata_schema.py`
- `tests/test_report_prompt_lint.py`
- `tests/test_example_report_snapshot.py`
- `tests/fixtures/external_metadata/` — fixtures for schema test (all-success, partial-failure, full-failure variants)

### 4.2 New data flow

```
user request
    |
    v
Claude extracts inputs
    |
    v
analyze.py -- produces -->  facts.json
                            aligned.cif
                            raw.json
    |
    v
Claude reads facts.json and report_prompt.md
    |
    v
Claude calls togomcp (Rich fetch set)       [NEW step]
    | list_databases
    | search_pdb_entity(id1)
    | search_pdb_entity(id2)
    | togoid_convertId(pdb->uniprot)
    | search_uniprot_entity(acc) x N
    | get_MIE_file(uniprot)
    | run_sparql(uniprot) x up to 2
    |
    v
Claude writes external_metadata.json        [NEW artifact]
    |
    v
Claude writes report.md
  (facts.json + external_metadata.json
   + training-data background with provenance)
    |
    v
Claude replies to user in Japanese
  (2-5 line summary + artifact paths)
```

### 4.3 New artifact: `external_metadata.json`

Schema (authoritative version lives in `schemas/external_metadata.schema.json`):

```json
{
  "fetched_at": "2026-04-09T12:00:00Z",
  "structures": {
    "<PDB_ID>": {
      "pdb_title": "<string or null>",
      "source": "togomcp:search_pdb_entity",
      "fetch_ok": true,
      "error": null
    }
  },
  "uniprot_mapping": {
    "pairs": [
      ["<PDB_ID>", "<UniProt_acc or null>"]
    ],
    "source": "togomcp:togoid_convertId",
    "fetch_ok": true,
    "error": null
  },
  "uniprot_entries": {
    "<UniProt_acc>": {
      "protein_names": "<string>",
      "organism": "<string>",
      "source": "togomcp:search_uniprot_entity",
      "fetch_ok": true,
      "error": null
    }
  },
  "uniprot_sparql": {
    "<UniProt_acc>": {
      "function": "<string or null>",
      "keywords": ["<keyword>", "..."],
      "domains": [{"name": "<string>", "range": "<string>"}],
      "source": "togomcp:run_sparql",
      "fetch_ok": true,
      "error": null
    }
  },
  "warnings": ["<string>"]
}
```

Every entry has a `fetch_ok` boolean and an optional `error` string. This makes it trivial for `report_prompt.md` to check whether a given piece of context is available before using it.

### 4.4 Graceful degradation

| Failure mode | Behavior |
|---|---|
| Single `search_pdb_entity` fails | Record `fetch_ok=false`, proceed. Structural Context subsection for that PDB uses training-data background only, marked `(general background)` |
| `togoid_convertId` fails or returns empty | Record failure. Structural Context Section 4a omits UniProt column; Section 4b and 4c rely on training data. |
| `search_uniprot_entity` fails for an accession | Record failure. Omit the UniProt row in the mini-table; keep PDB-derived facts. |
| 2 consecutive `run_sparql` failures | Pivot per togomcp usage guide. Skip SPARQL-derived content; the UniProt function and keyword subsection is omitted. |
| Whole `togomcp` server unreachable | Detected by a failure of the first call (`list_databases`); in that case, Claude skips all remaining togomcp calls and writes `external_metadata.json` with every section's `fetch_ok=false`, a top-level `warnings` entry containing the error message, and empty content fields. Section 4 of the report opens with "Structural context assembled from training data only; live DB lookup unavailable" and proceeds using `(general background)` markers only. |

The report is always produced. The skill never errors out because of a `togomcp` failure.

## 5. Report Structure (Shape 2)

The report is written in English, composed of 10 sections. Tables handle parallel data; prose handles synthesis. The drill-down condition is described in full below; condition variants follow in Section 5.11.

### 5.1 Section 1: Header

```
# <ID1> vs <ID2> — Conformational Comparison

*Generated <meta.generated_at in UTC>*

**Headline:** Overall Cα RMSD X.XX Å over N aligned residues
(Y % identity); M moved regions localized to <labels>, with max
Cα displacement D Å.
```

One paragraph, one sentence. Numbers drawn from `facts.alignment` and `facts.chain_summary[0].ca_displacement_stats`.

### 5.2 Section 2: Global Alignment Metrics

A single table. Columns: Metric, Value. Rows:

| Metric | Source |
|---|---|
| Alignment method | `facts.alignment.method` |
| Reference / Moved structure | `facts.alignment.reference`, `facts.alignment.moved` |
| Overall Cα RMSD | `facts.alignment.overall_rmsd_angstrom` |
| Refined RMSD | `facts.alignment.refined_rmsd_angstrom` |
| Aligned residues | `facts.alignment.n_aligned_residues` |
| Sequence identity | `facts.alignment.sequence_identity` (formatted as percent) |
| Chain A mean / median / p95 / max displacement | `facts.chain_summary[0].ca_displacement_stats` |
| Total \|ΔSASA\| | `facts.sasa_changes.total_delta_angstrom2` |
| Moved regions | `len(facts.moved_regions)` |

No prose in this section; the table speaks for itself.

### 5.3 Section 3: Moved Regions Comparison

Side-by-side table with one column per moved region (`facts.moved_regions`):

| Field | Region 1 | Region 2 | ... |
|---|---|---|---|
| Residue range | `residue_range_label` | | |
| n residues | `n_residues` | | |
| Mean / max Cα displacement | `mean_ca_displacement` / `max_ca_displacement` | | |
| Estimated rotation | `estimated_rotation_deg` | | |
| Estimated translation | `estimated_translation_angstrom` | | |
| Hinge candidate residues | `hinge_candidate_residues` | | |

Followed by 2–4 sentences comparing the regions: whether rotation/translation magnitudes are similar, whether one region dominates, whether hinges are adjacent. Run-derived only.

### 5.4 Section 4: Structural Context

The main new section, split into three subsections.

**Section 4a — Structure metadata mini-table.** Sourced entirely from `external_metadata.json`:

| Field | Structure 1 | Structure 2 |
|---|---|---|
| PDB ID | `inputs.structure_1.id` | `inputs.structure_2.id` |
| PDB title | `external_metadata.structures.<id>.pdb_title` | |
| UniProt | `external_metadata.uniprot_mapping.pairs` | |
| Organism | `external_metadata.uniprot_entries.<acc>.organism` | |
| Protein | `external_metadata.uniprot_entries.<acc>.protein_names` | |
| Provenance | `per RCSB, per UniProt (via togomcp)` | |

**Section 4b — DB-derived interpretation.** One paragraph. Uses only `external_metadata.json` facts, with `(per RCSB)` and `(per UniProt <acc>)` markers on every factual claim. Answers: what are these two structures, are they the same protein, what ligands are present, what state (apo/holo) does the PDB title suggest?

**Section 4c — Background and interpretation tied to moved regions.** One to two paragraphs. Uses Claude's training-data knowledge about the protein's known architecture and dynamics. Every claim carries `(general background)`. The paragraph MUST tie the background to at least one specific feature of this run (a moved region, a hinge residue, a specific motion magnitude), not float as standalone textbook content. Any mapping of moved-region labels to named subdomains is marked `(inferred from run)` unless verified against `external_metadata.uniprot_sparql.*.domains`, in which case it is marked `(per UniProt SPARQL)`.

### 5.5 Section 5: Top Cα Movers

A table of the top 10 from `facts.top_ca_movers`, with cross-referenced columns:

| Rank | Res num | Res name | Cα disp (Å) | In region | SS change | ΔSASA (Å²) |
|---|---|---|---|---|---|---|

- **In region** — derived by checking which `moved_regions.residue_range` contains `res_num`, or `—` if outside
- **SS change** — joined from `facts.ss_changes` on `res_num`; `—` if not present
- **ΔSASA** — joined from `facts.sasa_changes.top_increases` and `top_decreases` on `res_num`; `—` if not present

Followed by 1–2 sentences on spatial clustering (which region dominates, whether movers are contiguous, etc.).

### 5.6 Section 6: Secondary Structure Changes by Region

One table per moved region, plus an "Outside moved regions" table if any `ss_changes` fall outside.

Per-region table columns: Res num, Res name, SS before, SS after. Only rows where `res_num` falls inside the region's `residue_range`.

After each table, one sentence describing the pattern (e.g., "Nine of ten residues in 122–154 show E→C transitions, indicating extended β-sheet disruption across the strand").

### 5.7 Section 7: SASA Highlights

Two tables drawn from `facts.sasa_changes`:

**Top increases** (up to 10 rows from `top_increases`):

| Res num | Res name | ΔSASA (Å²) | In region |
|---|---|---|---|

**Top decreases** (up to 10 rows from `top_decreases`):

| Res num | Res name | ΔSASA (Å²) | In region |
|---|---|---|---|

Followed by 1–2 sentences describing the pattern (e.g., which region dominates increases, whether buried surface is being exposed).

### 5.8 Section 8: Integrated Interpretation

One to two paragraphs. This is the **only** section where run facts, DB facts, and training-data background are woven together. Every claim carries its provenance marker. The synthesis should:

- Pick up the dominant motion pattern from Sections 3, 5, 6, 7
- Relate it to the DB-derived identity and state from Section 4
- Relate it to the known conformational dynamics of the protein family (background)
- Explicitly flag any mismatch between expectation and observation

### 5.9 Section 9: Caveats and Limitations

Bullets (genuine enumeration). Includes:

- `facts.warnings` contents (low sequence identity, multiple models, etc.)
- Altloc residues present (`facts.altloc_residues`)
- `drill_down_flags` that were off, with reasons
- Any `external_metadata.warnings` entries
- Any `fetch_ok=false` entries that affected the report

### 5.10 Section 10: Artifacts and Reproduction

Bullets:

- `aligned.cif` — superposed structure
- `facts.json` — computed run facts
- `external_metadata.json` — DB lookup snapshot
- `raw.json` — raw ChimeraX output
- Reproduction command: `./analyze.py --in1 <id1> --in2 <id2> --out <dir>`

### 5.11 Condition variants

- **drill-down** (default): all 10 sections full, no special handling.
- **nearly_identical**: Section 3 replaces the region comparison table with the literal sentence "No moved regions identified.". Sections 5, 6, and 7 each keep their heading and are followed by the literal line "_No entries for this run._" in italics (i.e., sections are never silently omitted — the heading and the explicit empty-marker are always present so the reader can confirm coverage). Section 8 focuses on "why the structures are close" (same ligand state, low mutation count, same crystal form) drawing on `external_metadata.json`; all other sections normal.
- **diffuse_motion**: Section 3 replaces the region comparison table with the literal sentence "Motion detected but not localized to discrete regions.". Section 5 (Top Movers) is retained in full because it is the most informative view without localized regions. Sections 6 and 7 are rendered normally if `facts.ss_changes` or `facts.sasa_changes` has entries, otherwise use the same "_No entries for this run._" empty-marker as in `nearly_identical`. Section 8 interprets the diffuse motion (solvent interaction, crystal packing, dynamic domain, data quality).

### 5.12 Provenance markers (authoritative list)

| Marker | Meaning | Source |
|---|---|---|
| `(run-derived)` or unmarked | Fact from `facts.json` (numbers, residues, regions). Default for numeric statements. | `facts.json` |
| `(inferred from run)` | Claude's interpretation based on run facts alone (no DB, no background) | `facts.json` reasoning |
| `(per RCSB)` | Fact from PDB title via `togomcp search_pdb_entity` | `external_metadata.structures.*.pdb_title` |
| `(per UniProt <acc>)` | Fact from `togomcp search_uniprot_entity` | `external_metadata.uniprot_entries.<acc>` |
| `(per UniProt SPARQL)` | Fact from `togomcp run_sparql` on UniProt | `external_metadata.uniprot_sparql.*` |
| `(general background)` | Claude's training-data knowledge, not verified against any DB | Training data |

## 6. Concrete File Changes

### 6.1 `templates/report_prompt.md` — full rewrite

Current file (109 lines, Japanese, "no background" enforcement) is fully replaced. New structure:

1. Intro: role and inputs (`facts.json`, `external_metadata.json`)
2. Hard rules — exactly six, numbered, English:
   1. Every numerical value in the report must trace to `facts.json`. Do not invent, round differently, or alter numbers.
   2. Every DB-derived fact must come from `external_metadata.json` and carry the correct provenance marker from the table in this prompt.
   3. Training-data background is allowed but must be marked with `(general background)`. Background claims must be tied to a specific run feature, not stated in isolation.
   4. Do not fabricate literature citations. Any author-year reference (e.g., "Müller & Schulz 1992") is forbidden. Phrase uncertain context as general background or omit it.
   5. Use tables for parallel data (metrics, region comparison, residue listings). Use prose for synthesis and interpretation. Do not produce all-bullet-point reports.
   6. Write in English. Aim for depth; do not artificially pad or compress. Stop when every `facts.json` section and every available `external_metadata.json` field has been either used or explicitly skipped with reason.
3. Provenance markers (authoritative table from Section 5.12)
4. Report structure (restates Sections 1–10 with exact heading text and field mappings)
5. Condition variants (drill-down, nearly_identical, diffuse_motion differences)
6. Final self-check (checklist the model runs before writing)

### 6.2 `SKILL.md` — workflow and constraints rewrite

- `allowed-tools` frontmatter: add `mcp__togomcp__*`
- Workflow steps 5–8 rewritten to include the new togomcp fetch step (6), report write in English (7), Japanese chat reply (8)
- Hard Constraints section rewritten: remove "no background in report"; add "all numerical values trace to facts.json", "provenance markers required on DB-derived and background content", "do not fabricate literature citations", "external metadata persisted to `external_metadata.json`"
- Failure Modes table unchanged (error codes did not change)

### 6.3 New: `schemas/external_metadata.schema.json`

JSON Schema for the new artifact, matching the structure in Section 4.3 of this design.

### 6.4 `examples/1ake_vs_4ake/` — regenerate

- Keep `facts.json`, `aligned.cif`, `raw.json` as-is (they do not change)
- Regenerate `report.md` in new format
- Add `external_metadata.json` with the actual togomcp fetch for 1AKE/4AKE

### 6.5 No touches

The following files are **not** modified:

- `analyze.py`
- `chimerax_script.py`
- `compare_structures/*.py`
- `schemas/facts.schema.json`, `schemas/raw.schema.json`, `schemas/error.schema.json`
- All existing `tests/*.py`
- `docs/superpowers/specs/2026-04-09-compare-structures-design.md` (preserved as historical record)
- `pyproject.toml`

## 7. Testing and Validation

### 7.1 Existing tests: unchanged, must stay green

All tests under `tests/` (9 `test_*.py` modules plus `conftest.py`, totaling ~1165 lines) test the Python pipeline. Since the pipeline is untouched, these tests must pass with no modification. A failing existing test is a signal that Python-side code was touched by mistake — rollback.

### 7.2 New: `tests/test_external_metadata_schema.py`

Validates `examples/1ake_vs_4ake/external_metadata.json` against `schemas/external_metadata.schema.json` using `jsonschema`. Also validates synthetic fixtures for:

- All fetches successful
- Partial failure (one PDB fetch failed, UniProt succeeded)
- Full failure (all `fetch_ok=false`, top-level warning set)

### 7.3 New: `tests/test_report_prompt_lint.py`

Reads `templates/report_prompt.md` as text and checks structural invariants via regex:

- Presence of all 6 provenance markers in the provenance table
- Presence of Section 1–10 heading markers in order
- At least one mention of `(general background)`
- "Hard rules" section contains exactly 6 numbered items
- "Final self-check" section exists

This is a regression guard, not a content check.

### 7.4 New: `tests/test_example_report_snapshot.py`

Reads `examples/1ake_vs_4ake/report.md` and checks:

- H1 matches `# 1AKE vs 4AKE — Conformational Comparison`
- H2 headings for Sections 2–10 present in order
- Section 2 table contains "Overall Cα RMSD" and "8.24"
- Section 4a table contains "P69441" and "E. coli"
- Each of `(per RCSB)`, `(per UniProt`, `(general background)`, and one of `(run-derived)` / `(inferred from run)` appears at least once
- Regex `[A-Z][a-z]+\s*(&|and|et al\.?)\s*[A-Z]` matches zero times (no fake author-year citations)
- File is ASCII-dominant (ratio > 0.9) and contains zero CJK characters (regression guard on the English-only rule)

This is a loose snapshot: the prose content is not fixed, only structure and provenance presence.

### 7.5 Graceful degradation: manual test

The rewritten `docs/manual_review_checklist.md` includes these graceful-degradation entries:

- [ ] Simulate full togomcp failure by manually setting every `fetch_ok: false` in `examples/1ake_vs_4ake/external_metadata.json` and regenerating `report.md`. Verify Section 4 opens with "Structural context assembled from training data only; live DB lookup unavailable" and Sections 1–3 / 5–10 remain functionally correct
- [ ] Simulate partial failure (only SPARQL fails). Verify UniProt function/keyword content is absent but PDB title and UniProt basic identity remain

### 7.6 Condition variants: P1, deferred

- `nearly_identical`: fixture with two copies of the same structure. Manual review only, not automated. P1.
- `diffuse_motion`: requires a structure pair with global motion but no localizable regions; defer to a hand-crafted `tests/fixtures/diffuse_motion_facts.json` for prompt-branch-only testing. P1.

P0 for this design is drill-down on 1AKE vs 4AKE.

### 7.7 Definition of Done

The redesign is complete when:

1. `./analyze.py --in1 1AKE --in2 4AKE --out examples/1ake_vs_4ake` runs successfully and produces `facts.json`, `aligned.cif`, `raw.json` (existing behavior)
2. Claude, following `SKILL.md`, generates `external_metadata.json` and a new-format `report.md` in `examples/1ake_vs_4ake/`
3. Manual review by the user confirms:
   - [ ] Report is in English
   - [ ] Shape 2's 10 sections are present
   - [ ] Tables and prose play their intended roles
   - [ ] All 6 provenance markers appear at least once
   - [ ] No fabricated literature citations
   - [ ] Section 8 synthesis connects run facts, DB facts, and background coherently
4. `pytest tests/` passes (all existing tests green, new tests green)
5. This design file exists at the documented path; original spec preserved unchanged
6. Memory entries for rich-report format and no-length-caps feedback are present in `~/.claude/projects/-Users-nagaet-explain-conf-skill/memory/`

## 8. Open Questions and Future Work

- **Optional metadata caching**: If `external_metadata.json` already exists for a run, should step 6 skip the togomcp fetch? Not in this redesign; consider in a follow-up if reruns become common.
- **Domain annotations from UniProt SPARQL**: The current design fetches domain annotations if SPARQL succeeds but does not attempt to cross-reference them against the moved regions automatically. A future enhancement could auto-flag whether moved regions fall inside or outside annotated domains.
- **Multi-chain support**: The current design assumes a single dominant chain (consistent with the existing `facts.chain_summary[0]` convention). Multi-chain reports require extending the report structure and are out of scope here.
- **Japanese report variant**: If a Japanese-reading user ever needs the report content (not just the chat reply), a translation step could be added downstream. Out of scope for this redesign.

## 9. Related Work and References

- `docs/superpowers/specs/2026-04-09-compare-structures-design.md` — the original pipeline design; still authoritative for the analysis side
- `docs/superpowers/plans/2026-04-09-compare-structures-implementation.md` — the original implementation plan
- `~/.claude/projects/-Users-nagaet-explain-conf-skill/memory/feedback_scientific_reports_rich_format.md` — feedback memory that motivated this redesign
- `~/.claude/projects/-Users-nagaet-explain-conf-skill/memory/feedback_no_strict_length_caps.md` — feedback memory on length caps
- togomcp Usage Guide — empirical workflow rules and tool budget constraints that shape the fetch sequence in Section 4.2
