# compare-structures Rich Report Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the compare-structures report-authoring layer so that it produces a rich, expert-level English report that combines run facts, `togomcp`-derived DB metadata, and training-data background with strict provenance markers — without touching the existing Python analysis pipeline.

**Architecture:** All changes are confined to the report-authoring layer (`SKILL.md` workflow steps 5–8, `templates/report_prompt.md`, example artifacts, manual review checklist) plus one new artifact (`external_metadata.json`) with its JSON Schema. The Python pipeline (`analyze.py`, `compare_structures/*`, `facts.json`) is strictly off-limits. Existing tests must stay green throughout.

**Tech Stack:** Python 3.12, pytest, jsonschema, uv, ruff, Claude Code Skill framework, `togomcp` MCP server.

**Spec:** `docs/superpowers/specs/2026-04-09-compare-structures-rich-report-redesign.md`

**Branch:** `feature/rich-report-redesign-spec` (already contains the spec commit; continue on this branch)

---

## Pre-flight

### Task 0: Verify baseline

**Files:** None (verification only)

- [ ] **Step 1: Confirm branch**

```bash
cd /Users/nagaet/explain-conf-skill
git branch --show-current
```

Expected: `feature/rich-report-redesign-spec`. If on `main`, run `git checkout feature/rich-report-redesign-spec` first. If the branch does not exist, STOP and ask — the spec commit must already be present.

- [ ] **Step 2: Run the existing test suite as baseline**

```bash
uv run --with pytest --with numpy --with jsonschema --with click pytest tests/ -q
```

Expected: all tests pass (or only `chimerax`-marked tests skipped because ChimeraX is not available). Record the pass count. If any non-skipped test fails here, STOP — the baseline is broken and must be fixed before making changes.

- [ ] **Step 3: Confirm spec is committed**

```bash
git log --oneline -5
```

Expected: first line contains `docs: Add rich-report redesign spec for compare-structures`.

---

## Task 1: External metadata JSON Schema + fixtures + schema test

**Rationale:** The new artifact `external_metadata.json` is the contract between the togomcp fetch step and the report prompt. Locking its schema first pins down exactly what the prompt can rely on.

**Files:**
- Create: `schemas/external_metadata.schema.json`
- Create: `tests/fixtures/external_metadata/all_ok.json`
- Create: `tests/fixtures/external_metadata/partial_failure.json`
- Create: `tests/fixtures/external_metadata/all_failed.json`
- Create: `tests/test_external_metadata_schema.py`

- [ ] **Step 1: Create fixtures directory and the three fixture files**

Create `tests/fixtures/external_metadata/all_ok.json`:

```json
{
  "fetched_at": "2026-04-09T05:55:24.959900+00:00",
  "structures": {
    "1AKE": {
      "pdb_title": "STRUCTURE OF THE COMPLEX BETWEEN ADENYLATE KINASE FROM ESCHERICHIA COLI AND THE INHIBITOR AP5A REFINED AT 1.9 ANGSTROMS RESOLUTION: A MODEL FOR A CATALYTIC TRANSITION STATE",
      "source": "togomcp:search_pdb_entity",
      "fetch_ok": true,
      "error": null
    },
    "4AKE": {
      "pdb_title": "Structure of the apo form of Escherichia coli adenylate kinase",
      "source": "togomcp:search_pdb_entity",
      "fetch_ok": true,
      "error": null
    }
  },
  "uniprot_mapping": {
    "pairs": [["1AKE", "P69441"], ["4AKE", "P69441"]],
    "source": "togomcp:togoid_convertId",
    "fetch_ok": true,
    "error": null
  },
  "uniprot_entries": {
    "P69441": {
      "protein_names": "Adenylate kinase (AK) (EC 2.7.4.3) (ATP-AMP transphosphorylase) (ATP:AMP phosphotransferase) (Adenylate monophosphate kinase)",
      "organism": "Escherichia coli (strain K12)",
      "source": "togomcp:search_uniprot_entity",
      "fetch_ok": true,
      "error": null
    }
  },
  "uniprot_sparql": {
    "P69441": {
      "function": "Catalyzes the reversible transfer of the terminal phosphate group between ATP and AMP.",
      "keywords": ["Kinase", "Nucleotide-binding", "ATP-binding", "Transferase"],
      "domains": [{"name": "Adenylate kinase", "range": "1-214"}],
      "source": "togomcp:run_sparql",
      "fetch_ok": true,
      "error": null
    }
  },
  "warnings": []
}
```

Create `tests/fixtures/external_metadata/partial_failure.json`:

```json
{
  "fetched_at": "2026-04-09T06:00:00.000000+00:00",
  "structures": {
    "1AKE": {
      "pdb_title": "STRUCTURE OF THE COMPLEX BETWEEN ADENYLATE KINASE FROM ESCHERICHIA COLI AND THE INHIBITOR AP5A REFINED AT 1.9 ANGSTROMS RESOLUTION: A MODEL FOR A CATALYTIC TRANSITION STATE",
      "source": "togomcp:search_pdb_entity",
      "fetch_ok": true,
      "error": null
    },
    "4AKE": {
      "pdb_title": null,
      "source": "togomcp:search_pdb_entity",
      "fetch_ok": false,
      "error": "Empty result set"
    }
  },
  "uniprot_mapping": {
    "pairs": [["1AKE", "P69441"], ["4AKE", "P69441"]],
    "source": "togomcp:togoid_convertId",
    "fetch_ok": true,
    "error": null
  },
  "uniprot_entries": {
    "P69441": {
      "protein_names": "Adenylate kinase (AK) (EC 2.7.4.3)",
      "organism": "Escherichia coli (strain K12)",
      "source": "togomcp:search_uniprot_entity",
      "fetch_ok": true,
      "error": null
    }
  },
  "uniprot_sparql": {
    "P69441": {
      "function": null,
      "keywords": [],
      "domains": [],
      "source": "togomcp:run_sparql",
      "fetch_ok": false,
      "error": "2 consecutive SPARQL failures; pivoted per togomcp usage guide"
    }
  },
  "warnings": ["SPARQL path failed after pivot; uniprot_sparql omitted"]
}
```

Create `tests/fixtures/external_metadata/all_failed.json`:

```json
{
  "fetched_at": "2026-04-09T06:00:00.000000+00:00",
  "structures": {
    "1AKE": {
      "pdb_title": null,
      "source": "togomcp:search_pdb_entity",
      "fetch_ok": false,
      "error": "togomcp server unreachable"
    },
    "4AKE": {
      "pdb_title": null,
      "source": "togomcp:search_pdb_entity",
      "fetch_ok": false,
      "error": "togomcp server unreachable"
    }
  },
  "uniprot_mapping": {
    "pairs": [],
    "source": "togomcp:togoid_convertId",
    "fetch_ok": false,
    "error": "togomcp server unreachable"
  },
  "uniprot_entries": {},
  "uniprot_sparql": {},
  "warnings": [
    "togomcp list_databases failed; all subsequent togomcp calls skipped",
    "Structural context will be authored from training data only"
  ]
}
```

- [ ] **Step 2: Write the failing schema test**

Create `tests/test_external_metadata_schema.py`:

```python
"""Tests for schemas/external_metadata.schema.json."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCHEMA_PATH = _REPO_ROOT.joinpath("schemas", "external_metadata.schema.json")
_FIXTURE_DIR = Path(__file__).parent.joinpath("fixtures", "external_metadata")


def _load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text())


def _load_fixture(name: str) -> dict:
    return json.loads((_FIXTURE_DIR / name).read_text())


def test_schema_is_valid_draft_2020_12():
    """The schema itself must be a valid Draft 2020-12 schema."""
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize(
    "fixture_name",
    ["all_ok.json", "partial_failure.json", "all_failed.json"],
)
def test_fixture_validates(fixture_name: str):
    """Every bundled fixture must validate against the schema."""
    schema = _load_schema()
    instance = _load_fixture(fixture_name)
    Draft202012Validator(schema).validate(instance)


def test_missing_required_top_level_key_fails():
    """Dropping a required top-level key must fail validation."""
    schema = _load_schema()
    instance = _load_fixture("all_ok.json")
    del instance["structures"]
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)


def test_fetch_ok_must_be_bool():
    """fetch_ok fields must be booleans, not strings."""
    schema = _load_schema()
    instance = _load_fixture("all_ok.json")
    instance["structures"]["1AKE"]["fetch_ok"] = "yes"
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)


def test_source_must_start_with_togomcp_prefix():
    """Every source field must be prefixed with 'togomcp:'."""
    schema = _load_schema()
    instance = _load_fixture("all_ok.json")
    instance["structures"]["1AKE"]["source"] = "manual"
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)
```

- [ ] **Step 3: Run the test to verify it fails**

```bash
uv run --with pytest --with jsonschema pytest tests/test_external_metadata_schema.py -v
```

Expected: all tests fail with `FileNotFoundError` or similar on the schema load, because the schema file does not yet exist.

- [ ] **Step 4: Create the schema file**

Create `schemas/external_metadata.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "compare-structures external_metadata.json",
  "type": "object",
  "required": [
    "fetched_at",
    "structures",
    "uniprot_mapping",
    "uniprot_entries",
    "uniprot_sparql",
    "warnings"
  ],
  "properties": {
    "fetched_at": {
      "type": "string",
      "description": "ISO 8601 UTC timestamp when the togomcp fetch began."
    },
    "structures": {
      "type": "object",
      "description": "Per-PDB-ID structure metadata keyed by PDB ID.",
      "additionalProperties": {
        "type": "object",
        "required": ["pdb_title", "source", "fetch_ok", "error"],
        "properties": {
          "pdb_title": {"type": ["string", "null"]},
          "source": {"type": "string", "pattern": "^togomcp:"},
          "fetch_ok": {"type": "boolean"},
          "error": {"type": ["string", "null"]}
        },
        "additionalProperties": false
      }
    },
    "uniprot_mapping": {
      "type": "object",
      "required": ["pairs", "source", "fetch_ok", "error"],
      "properties": {
        "pairs": {
          "type": "array",
          "items": {
            "type": "array",
            "prefixItems": [
              {"type": "string"},
              {"type": ["string", "null"]}
            ],
            "minItems": 2,
            "maxItems": 2
          }
        },
        "source": {"type": "string", "pattern": "^togomcp:"},
        "fetch_ok": {"type": "boolean"},
        "error": {"type": ["string", "null"]}
      },
      "additionalProperties": false
    },
    "uniprot_entries": {
      "type": "object",
      "description": "Per-UniProt-accession entry metadata keyed by accession.",
      "additionalProperties": {
        "type": "object",
        "required": ["protein_names", "organism", "source", "fetch_ok", "error"],
        "properties": {
          "protein_names": {"type": ["string", "null"]},
          "organism": {"type": ["string", "null"]},
          "source": {"type": "string", "pattern": "^togomcp:"},
          "fetch_ok": {"type": "boolean"},
          "error": {"type": ["string", "null"]}
        },
        "additionalProperties": false
      }
    },
    "uniprot_sparql": {
      "type": "object",
      "description": "Per-UniProt-accession SPARQL-derived detail keyed by accession.",
      "additionalProperties": {
        "type": "object",
        "required": ["function", "keywords", "domains", "source", "fetch_ok", "error"],
        "properties": {
          "function": {"type": ["string", "null"]},
          "keywords": {
            "type": "array",
            "items": {"type": "string"}
          },
          "domains": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["name", "range"],
              "properties": {
                "name": {"type": "string"},
                "range": {"type": "string"}
              },
              "additionalProperties": false
            }
          },
          "source": {"type": "string", "pattern": "^togomcp:"},
          "fetch_ok": {"type": "boolean"},
          "error": {"type": ["string", "null"]}
        },
        "additionalProperties": false
      }
    },
    "warnings": {
      "type": "array",
      "items": {"type": "string"}
    }
  },
  "additionalProperties": false
}
```

- [ ] **Step 5: Run the test and verify it passes**

```bash
uv run --with pytest --with jsonschema pytest tests/test_external_metadata_schema.py -v
```

Expected: all 6 test cases pass (`test_schema_is_valid_draft_2020_12`, `test_fixture_validates[all_ok.json]`, `test_fixture_validates[partial_failure.json]`, `test_fixture_validates[all_failed.json]`, `test_missing_required_top_level_key_fails`, `test_fetch_ok_must_be_bool`, `test_source_must_start_with_togomcp_prefix`).

- [ ] **Step 6: Commit**

```bash
git add schemas/external_metadata.schema.json \
        tests/fixtures/external_metadata/ \
        tests/test_external_metadata_schema.py
git commit -m "$(cat <<'EOF'
feat: Add external_metadata.json schema and validation tests

Defines the JSON Schema for the new external_metadata.json artifact
that stores togomcp fetch results alongside facts.json. Includes
fixtures for all-success, partial-failure, and full-failure cases
and unit tests asserting schema validity and fixture conformance.
EOF
)"
```

---

## Task 2: Report prompt lint test + prompt rewrite

**Rationale:** The prompt is the primary artifact driving report quality. A structural lint test pins down the 10-section skeleton, 6 hard rules, and 6 provenance markers so that future edits cannot accidentally strip them.

**Files:**
- Create: `tests/test_report_prompt_lint.py`
- Modify (full rewrite): `templates/report_prompt.md`

- [ ] **Step 1: Write the failing lint test**

Create `tests/test_report_prompt_lint.py`:

```python
"""Structural lint for templates/report_prompt.md.

Does not check prose content; only that the required structural
elements (hard rules, provenance markers, section skeleton, final
self-check) are present.
"""

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PROMPT_PATH = _REPO_ROOT.joinpath("templates", "report_prompt.md")


@pytest.fixture(scope="module")
def prompt_text() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def test_prompt_file_exists(prompt_text: str):
    assert len(prompt_text) > 0, "report_prompt.md is empty"


def test_prompt_is_english(prompt_text: str):
    """No CJK characters allowed; report must be authored in English."""
    cjk = re.findall(r"[\u3000-\u9fff]", prompt_text)
    assert cjk == [], f"Prompt contains CJK characters: {cjk[:10]}"


def test_six_hard_rules_present(prompt_text: str):
    """The hard-rules section must contain exactly 6 numbered items."""
    hard_rules_block = re.search(
        r"## Hard rules(.+?)(?=\n## )",
        prompt_text,
        re.DOTALL,
    )
    assert hard_rules_block, "Missing '## Hard rules' section"
    numbered = re.findall(r"^\s*(\d+)\.\s", hard_rules_block.group(1), re.MULTILINE)
    assert numbered == ["1", "2", "3", "4", "5", "6"], (
        f"Expected exactly 6 numbered hard rules, got {numbered}"
    )


@pytest.mark.parametrize(
    "marker",
    [
        "(run-derived)",
        "(inferred from run)",
        "(per RCSB)",
        "(per UniProt",
        "(per UniProt SPARQL)",
        "(general background)",
    ],
)
def test_provenance_marker_listed(prompt_text: str, marker: str):
    """Every provenance marker must appear in the prompt."""
    assert marker in prompt_text, f"Provenance marker {marker!r} missing from prompt"


@pytest.mark.parametrize(
    "heading",
    [
        "Section 1: Header",
        "Section 2: Global Alignment Metrics",
        "Section 3: Moved Regions Comparison",
        "Section 4: Structural Context",
        "Section 5: Top C\u03b1 Movers",
        "Section 6: Secondary Structure Changes by Region",
        "Section 7: SASA Highlights",
        "Section 8: Integrated Interpretation",
        "Section 9: Caveats and Limitations",
        "Section 10: Artifacts and Reproduction",
    ],
)
def test_ten_section_skeleton(prompt_text: str, heading: str):
    assert heading in prompt_text, f"Missing section heading: {heading}"


def test_section_order(prompt_text: str):
    """Sections 1-10 must appear in order."""
    positions = []
    for n in range(1, 11):
        match = re.search(rf"Section {n}:", prompt_text)
        assert match, f"Section {n} header missing"
        positions.append(match.start())
    assert positions == sorted(positions), (
        f"Sections are out of order: {positions}"
    )


def test_condition_variants_documented(prompt_text: str):
    for label in ("drill-down", "nearly_identical", "diffuse_motion"):
        assert label in prompt_text, f"Condition variant '{label}' not documented"


def test_empty_marker_string(prompt_text: str):
    """The literal empty-section marker used in condition variants."""
    assert "_No entries for this run._" in prompt_text


def test_final_self_check_present(prompt_text: str):
    assert "## Final self-check" in prompt_text or "## Final Self-Check" in prompt_text


def test_general_background_marker_referenced(prompt_text: str):
    """The prompt must instruct the model to mark background explicitly."""
    assert prompt_text.count("(general background)") >= 2
```

- [ ] **Step 2: Run the lint test to verify it fails**

```bash
uv run --with pytest pytest tests/test_report_prompt_lint.py -v
```

Expected: multiple failures — the current `templates/report_prompt.md` is Japanese, contains a different structure, and has none of the required markers. Many tests will report "Prompt contains CJK characters" or "Missing section heading". This is the intended red state.

- [ ] **Step 3: Fully rewrite `templates/report_prompt.md`**

Replace the entire file contents with the English prompt below. Use `Write` (not `Edit`) because every line is being replaced.

```markdown
# compare-structures report authoring prompt

You are writing a rich, expert-level structural-comparison report for a
structural-biology research audience. Your inputs are:

1. `facts.json` — the authoritative run-derived facts produced by the
   ChimeraX pipeline for this specific comparison.
2. `external_metadata.json` — DB lookups (PDB titles, UniProt mapping,
   UniProt entries, UniProt SPARQL details) already fetched by earlier
   workflow steps. Every sub-object has a `fetch_ok` boolean indicating
   whether the underlying call succeeded.

Your output is `report.md`, written in English, following the Shape 2
table-first structure defined below.

## Hard rules

These rules are non-negotiable. A report that violates any of them is
worse than no report.

1. Every numerical value in the report must trace to `facts.json`. Do
   not invent values, do not round differently, and do not alter numbers.
2. Every DB-derived fact must come from `external_metadata.json` and
   carry the correct provenance marker from the table in this prompt.
3. Training-data background is allowed but must be marked with
   `(general background)`. Background claims must be tied to a specific
   run feature; do not state background as a standalone textbook entry.
4. Do not fabricate literature citations. Any author-year reference
   (for example `Müller & Schulz 1992` or `Smith et al. 2020`) is
   forbidden. Phrase uncertain context as `(general background)` or
   omit it.
5. Use tables for parallel data (metrics, region comparison, residue
   listings). Use prose for synthesis and interpretation. Do not
   produce all-bullet-point reports. Bullets are reserved for genuine
   enumerations (Caveats, Artifacts).
6. Write in English. Aim for depth, not padding. Do not artificially
   compress. Stop writing when every `facts.json` section and every
   available `external_metadata.json` field has been either used or
   explicitly skipped with a reason.

## Provenance markers

Every factual claim in the report must be attributable to one of these
six provenance markers. Numbers from `facts.json` are `(run-derived)`
and the marker may be omitted when the numeric origin is obvious from
context, but any interpretive claim must be explicitly marked.

| Marker                  | Meaning                                                                          | Source                                         |
|-------------------------|----------------------------------------------------------------------------------|------------------------------------------------|
| `(run-derived)`         | Fact from `facts.json` (numbers, residues, regions). Default for numeric values. | `facts.json`                                   |
| `(inferred from run)`   | Interpretation based only on run facts, no DB or background input.               | `facts.json` reasoning                         |
| `(per RCSB)`            | Fact from a PDB title fetched via `togomcp:search_pdb_entity`.                   | `external_metadata.structures.*.pdb_title`     |
| `(per UniProt <acc>)`   | Fact from a UniProt entry fetched via `togomcp:search_uniprot_entity`.           | `external_metadata.uniprot_entries.<acc>`      |
| `(per UniProt SPARQL)`  | Fact from a UniProt SPARQL query via `togomcp:run_sparql`.                       | `external_metadata.uniprot_sparql.*`           |
| `(general background)`  | Claude's training-data knowledge, not verified against any DB in this run.       | Training data                                  |

## Report structure (Shape 2 — table-first)

Write the sections in the listed order. Every section heading must
appear exactly as shown below, as a level-2 markdown heading (`## …`).
Never silently omit a section; if a section has no content under the
current condition, render the heading and an explicit empty marker
`_No entries for this run._`.

### Section 1: Header

Render as:

```
# <ID1> vs <ID2> — Conformational Comparison

*Generated <meta.generated_at formatted as UTC>*

**Headline:** <one sentence containing overall Cα RMSD in Å,
n aligned residues, sequence identity as percent, number of moved
regions, and the largest max Cα displacement in Å>.
```

### Section 2: Global Alignment Metrics

A single markdown table with two columns (`Metric`, `Value`) and no
prose. Include these rows, in this order, pulling values from
`facts.alignment`, `facts.chain_summary[0].ca_displacement_stats`, and
`facts.sasa_changes.total_delta_angstrom2`:

1. Alignment method — `facts.alignment.method`
2. Reference / Moved structure — `facts.alignment.reference` /
   `facts.alignment.moved`
3. Overall Cα RMSD — `facts.alignment.overall_rmsd_angstrom` Å
4. Refined RMSD — `facts.alignment.refined_rmsd_angstrom` Å
5. Aligned residues — `facts.alignment.n_aligned_residues`
6. Sequence identity — `facts.alignment.sequence_identity` formatted
   as a percent to one decimal place
7. Chain A displacement (mean / median / p95 / max) —
   from `facts.chain_summary[0].ca_displacement_stats`, all in Å
8. Total |ΔSASA| — `facts.sasa_changes.total_delta_angstrom2` Å²
9. Moved regions — `len(facts.moved_regions)`

### Section 3: Moved Regions Comparison

A markdown table with one column per entry in `facts.moved_regions`
(so two columns of values for two regions, three for three, and so
on). Rows:

- Residue range — `residue_range_label`
- n residues — `n_residues`
- Mean / max Cα displacement — `mean_ca_displacement` /
  `max_ca_displacement`, both in Å
- Estimated rotation — `estimated_rotation_deg`, degrees
- Estimated translation — `estimated_translation_angstrom`, Å
- Hinge candidate residues — `hinge_candidate_residues` as a
  comma-separated list

After the table, write 2 to 4 sentences comparing the regions. Cover
whether the rotations are similar, whether one region dominates in
displacement, and whether the hinges are adjacent. Run-derived content
only (no background in this section).

If `facts.moved_regions` is empty, replace the table with the literal
sentence `No discrete moved regions identified.` and skip the
comparative prose.

### Section 4: Structural Context

This is the only section where DB-derived facts and training-data
background are combined. Render it as three subsections.

#### Section 4a: Structure metadata

A markdown table with three columns (`Field`, `Structure 1`,
`Structure 2`) and these rows:

- `PDB ID`
- `PDB title` — `external_metadata.structures.<id>.pdb_title` when
  `fetch_ok`; otherwise `_not available_`
- `UniProt` — from `external_metadata.uniprot_mapping.pairs`
- `Organism` — `external_metadata.uniprot_entries.<acc>.organism`
  when `fetch_ok`
- `Protein` — `external_metadata.uniprot_entries.<acc>.protein_names`
  when `fetch_ok`
- `Provenance` — a short phrase describing the sources, e.g.
  `per RCSB, per UniProt P69441 (via togomcp)` or
  `_DB lookup unavailable_` if every fetch failed

#### Section 4b: DB-derived interpretation

One paragraph drawing only on `external_metadata.json`. Every factual
claim must carry `(per RCSB)`, `(per UniProt <acc>)`, or
`(per UniProt SPARQL)`. Cover: what are the two structures, are they
the same protein, what ligands or state do the PDB titles suggest,
and what functional annotations are available.

If all `fetch_ok` fields are false, replace this subsection with the
single sentence `Structural context assembled from training data
only; live DB lookup unavailable.`

#### Section 4c: Background and motion interpretation

One or two paragraphs drawing on training-data knowledge of the
protein's architecture and dynamics. Every claim must carry
`(general background)`. Each paragraph must tie the background to a
specific feature of this run (a moved region label, a hinge residue,
a specific motion magnitude). Free-floating textbook content is
forbidden.

If you map a moved-region range to a named subdomain (e.g.
"corresponds to the LID subdomain"), mark this as
`(inferred from run)` unless `external_metadata.uniprot_sparql.<acc>.domains`
contains a domain whose range overlaps the moved region, in which
case mark it `(per UniProt SPARQL)`.

### Section 5: Top Cα Movers

A markdown table of the top entries in `facts.top_ca_movers` (up to
ten). Columns:

- `Rank` — 1-based index
- `Res num` — `res_num`
- `Res name` — `res_name`
- `Cα disp (Å)` — `displacement`
- `In region` — the `residue_range_label` of the moved region that
  contains `res_num`, or `—` if none
- `SS change` — joined from `facts.ss_changes` on `res_num` as
  `<before>→<after>`, or `—`
- `ΔSASA (Å²)` — joined from `facts.sasa_changes.top_increases` and
  `top_decreases` on `res_num`, signed, or `—`

After the table, write 1 or 2 sentences describing spatial clustering:
which region dominates, whether the movers are contiguous, whether
the maximum sits at the edge or the middle of a region.

### Section 6: Secondary Structure Changes by Region

For each entry in `facts.moved_regions`, write a subsection with an
H4 heading `Region <k> (<residue_range_label>)` followed by a table
with columns (`Res num`, `Res name`, `Before`, `After`) listing every
`ss_change` whose `res_num` lies inside the region range, in ascending
`res_num` order.

After each per-region table, write one sentence describing the
pattern (for example: "Nine of ten residues in 122–154 show E→C,
indicating extended β-sheet disruption across the strand").

If any `ss_changes` fall outside every moved region, write a final
subsection `Outside moved regions` with the same table columns.

If `facts.ss_changes` is empty, replace the whole section body with
`_No entries for this run._`.

### Section 7: SASA Highlights

Two markdown tables drawn from `facts.sasa_changes`.

First, `Top increases`: the entries from `top_increases` (up to ten),
columns `Res num`, `Res name`, `ΔSASA (Å²)`, `In region`. The
`In region` column is the `residue_range_label` of the containing
moved region, or `—`.

Second, `Top decreases`: the entries from `top_decreases` (up to ten),
same columns.

After both tables, write 1 or 2 sentences on the dominant pattern
(which region gains the most exposed surface, whether residues
bury or expose).

If both `top_increases` and `top_decreases` are empty, replace the
whole section body with `_No entries for this run._`.

### Section 8: Integrated Interpretation

One or two paragraphs of prose synthesis. This is the only section
where run facts, DB facts, and training-data background may be woven
together in the same sentence. Every factual claim must carry its
provenance marker. Structure the synthesis to cover, in order:

- The dominant motion pattern you derived from Sections 3, 5, 6, 7.
- The structural identity of the two states from Section 4.
- The known conformational dynamics of the protein family
  (background), tied to the motion pattern above.
- Any mismatch between expectation and the run observations.

### Section 9: Caveats and Limitations

Bullets (genuine enumeration; this is the one section where a
bullet-only block is correct). Include:

- Every string in `facts.warnings`.
- Every residue in `facts.altloc_residues.structure_1` and
  `facts.altloc_residues.structure_2`, grouped by structure.
- Any `drill_down_flags` entry whose value is false, with the
  `reasons` string.
- Any `external_metadata.warnings` entry.
- Any `fetch_ok: false` in `external_metadata` that materially
  affected the report.

If none of these bullets have content, write `_No caveats for this
run._`.

### Section 10: Artifacts and Reproduction

Bullets listing the artifacts in the run directory, then the
reproduction command:

- `aligned.cif` — superposed structure
- `facts.json` — computed run facts
- `external_metadata.json` — DB lookup snapshot
- `raw.json` — raw ChimeraX output
- Reproduction: `./analyze.py --in1 <id1> --in2 <id2> --out <dir>`

## Condition variants

The condition is indicated by `facts.condition`. Handle it as follows:

### drill-down (default; `condition` is null or unset and
`facts.moved_regions` is non-empty)

Render all 10 sections as specified above. No special handling.

### nearly_identical (`condition == "structures_nearly_identical"`)

- Section 3 replaces the comparison table with the literal sentence
  `No moved regions identified.`.
- Sections 5, 6, and 7 keep their headings and use the literal empty
  marker `_No entries for this run._` under each heading.
- Section 8 shifts focus: instead of interpreting motion, interpret
  why the structures are close. Cover ligand state sameness, mutation
  count, and crystal-form sameness using `external_metadata.json` and
  `(general background)` markers.
- All other sections behave normally.

### diffuse_motion (`condition == "diffuse_motion"`)

- Section 3 replaces the comparison table with the literal sentence
  `Motion detected but not localized to discrete regions.`.
- Section 5 (Top Movers) is retained in full — it is the most
  informative view when regions cannot be localized.
- Sections 6 and 7 are rendered normally if `facts.ss_changes` or
  `facts.sasa_changes` has entries; otherwise use the empty marker.
- Section 8 interprets the diffuse motion (solvent interaction,
  crystal packing, dynamic domain, data quality).

## Final self-check

Before saving `report.md`, read it back and confirm every item below.
If any check fails, fix the report before saving.

- [ ] Every numerical value in the report traces to `facts.json`.
- [ ] Every DB-derived factual claim has a provenance marker
      (`(per RCSB)`, `(per UniProt <acc>)`, or `(per UniProt SPARQL)`).
- [ ] Every background claim has `(general background)` and is tied
      to a run feature.
- [ ] No author-year literature citations appear anywhere.
- [ ] Tables are used for parallel data; prose is used for synthesis;
      bullets are used only in Sections 9 and 10.
- [ ] The report is in English. No CJK characters.
- [ ] All 10 sections are present, in order, either with content or
      with the literal empty marker `_No entries for this run._`.
- [ ] The report's depth reflects the amount of data in this run and
      is not artificially padded or compressed.
```

- [ ] **Step 4: Run the lint test to verify it passes**

```bash
uv run --with pytest pytest tests/test_report_prompt_lint.py -v
```

Expected: all lint test cases pass.

- [ ] **Step 5: Run the full test suite to verify nothing regressed**

```bash
uv run --with pytest --with numpy --with jsonschema --with click pytest tests/ -q
```

Expected: baseline tests still pass plus the new schema and lint tests.

- [ ] **Step 6: Commit**

```bash
git add templates/report_prompt.md tests/test_report_prompt_lint.py
git commit -m "$(cat <<'EOF'
feat: Rewrite report_prompt.md for rich English Shape 2 output

Replaces the old Japanese facts-only prompt with a new English prompt
that specifies the 10-section Shape 2 structure, six hard rules, six
provenance markers, condition variants, and a final self-check. Adds
a structural lint test that pins the skeleton so future edits cannot
drop required elements.
EOF
)"
```

---

## Task 3: SKILL.md rewrite

**Rationale:** `SKILL.md` is the contract that Claude follows at runtime. It must reflect the new togomcp fetch step, the new hard constraints, and the new allowed tools.

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: Update the frontmatter**

Open `SKILL.md` and change the `allowed-tools` line from `allowed-tools: Read, Write, Bash` to `allowed-tools: Read, Write, Bash, mcp__togomcp__*`.

- [ ] **Step 2: Replace the Workflow section steps 5 through 7**

Find the current workflow block (steps 5–7, approximately lines 43–57) and replace it with the block below. Leave steps 1–4 unchanged.

```markdown
5. **Read the facts and the prompt.** Use `Read` to load:
   - `<output_dir>/facts.json`
   - `<skill_dir>/templates/report_prompt.md`

6. **Fetch external metadata via togomcp.** Call the togomcp tools in
   this order, recording each result into an in-memory metadata object
   shaped by `schemas/external_metadata.schema.json`:

   1. `mcp__togomcp__list_databases()` — once per session. If this
      call fails, skip all remaining togomcp calls and record a
      top-level warning "togomcp list_databases failed; all
      subsequent togomcp calls skipped".
   2. `mcp__togomcp__search_pdb_entity(db="pdb", query=<id1>)` and
      `mcp__togomcp__search_pdb_entity(db="pdb", query=<id2>)`.
      Record each `pdb_title`, `fetch_ok`, and any error.
   3. `mcp__togomcp__togoid_convertId(ids="<id1>,<id2>",
      route="pdb,uniprot")`. Record the returned `pairs`.
   4. For each unique UniProt accession in the pairs:
      `mcp__togomcp__search_uniprot_entity(
       query="accession:<ACC> AND reviewed:true", limit=1)`.
      Record `protein_names` and `organism`.
   5. `mcp__togomcp__get_MIE_file(dbname="uniprot")` — only if you
      intend to run SPARQL.
   6. `mcp__togomcp__run_sparql(dbname="uniprot", sparql_query=...)`
      to fetch function, keywords, and domains for each unique
      accession. Maximum two SPARQL calls total. On two consecutive
      failures, stop and record a warning; do not retry further.

   Use `Write` to save the accumulated object to
   `<output_dir>/external_metadata.json`. The file must validate
   against `schemas/external_metadata.schema.json`.

7. **Write the report.** Following `templates/report_prompt.md`
   strictly, use `Write` to create `<output_dir>/report.md`.

   The report MUST be in English. The prompt's hard rules
   (provenance markers, no fabricated citations, table-first
   structure, no length cap) are enforced by the prompt itself.
```

- [ ] **Step 3: Renumber the existing step 7 (Reply to user) as step 8 and adjust its body**

Find the "Reply to the user" block immediately below the Write-report block and replace it with:

```markdown
8. **Reply to the user in Japanese.** 2–5 lines summarizing:
   - The headline metrics (overall Cα RMSD, n aligned residues,
     number of moved regions).
   - Any togomcp fetch warnings (if the `warnings` list in
     `external_metadata.json` is non-empty, mention it briefly).
   - Paths to the artifacts: `report.md`, `aligned.cif`,
     `facts.json`, and `external_metadata.json`.

   Example:
   > 1AKE と 4AKE の比較が完了しました。全体 Cα RMSD は 8.24 Å、
   > 動いた領域は A/32-70 と A/117-166 の2箇所。DB lookup は正常。
   > 詳細は `runs/1AKE_vs_4AKE_20260409_124530/report.md` を参照。
```

- [ ] **Step 4: Replace the Hard Constraints section**

Find the `## Hard Constraints` heading and replace its bullet list with:

```markdown
## Hard Constraints

- **All numerical values in the report must trace to `facts.json`.**
  Claude may not invent or alter run-derived numbers.
- **All DB-derived facts must carry a provenance marker** pointing at
  the togomcp source (see `templates/report_prompt.md` for the six
  markers). Training-data background is allowed but must be marked
  with `(general background)` and tied to a specific run feature.
- **Do not fabricate literature citations.** Author-year references
  must not appear in the report.
- **Do not skip the pipeline.** Never write a report without running
  `analyze.py` — the report must reflect the actual `facts.json` for
  this run.
- **Do not modify `facts.json`.** It is a generated artifact.
- **External metadata is persisted.** The togomcp fetch results must
  be saved to `<output_dir>/external_metadata.json` as a separate
  artifact, independent of `facts.json`, and must validate against
  `schemas/external_metadata.schema.json`.
- **The report is written in English.** The Japanese chat reply
  (step 8) remains Japanese, but `report.md` itself is English.
```

- [ ] **Step 5: Run the full test suite**

```bash
uv run --with pytest --with numpy --with jsonschema --with click pytest tests/ -q
```

Expected: all tests pass. (SKILL.md is not tested automatically; this run guards against accidental Python-side damage.)

- [ ] **Step 6: Commit**

```bash
git add SKILL.md
git commit -m "$(cat <<'EOF'
feat: Rewrite SKILL.md workflow for rich report with togomcp fetch

Adds the togomcp external-metadata fetch as workflow step 6, renumbers
user reply to step 8, rewrites the hard-constraints section to remove
the no-background rule and require provenance markers, and extends
allowed-tools to include mcp__togomcp__*.
EOF
)"
```

---

## Task 4: Manual review checklist rewrite

**Rationale:** The existing `docs/manual_review_checklist.md` enforces the now-reversed no-background rule and a 600–1200 Japanese character length target. Appending to it is incoherent; it must be fully rewritten to match the new design.

**Files:**
- Modify (full rewrite): `docs/manual_review_checklist.md`

- [ ] **Step 1: Replace the file contents**

Use `Write` (not `Edit`) to overwrite `docs/manual_review_checklist.md` with:

```markdown
# Manual Review Checklist — Generated `report.md`

Automated tests cover structural invariants (Shape 2 skeleton,
provenance markers present, English-only, no fabricated citations).
They cannot validate prose quality or content correctness. Use this
checklist when reviewing a new sample report during development or
when diagnosing a regression.

## 1. Language and format

- [ ] The report is in English. No CJK characters anywhere.
- [ ] All 10 sections are present in order, with the exact H2 headings
      defined in `templates/report_prompt.md`.
- [ ] Tables are used for parallel data (metrics, region comparison,
      residue listings). Prose is used for synthesis and
      interpretation. Bullets appear only in Sections 9 and 10.
- [ ] No section is silently omitted. When a section has no content
      under the current condition, it uses the literal empty marker
      `_No entries for this run._`.

## 2. Numeric agreement with `facts.json`

For every numeric value in the report, confirm the same value appears
in `facts.json`:

- [ ] Overall Cα RMSD matches `alignment.overall_rmsd_angstrom`.
- [ ] Refined RMSD matches `alignment.refined_rmsd_angstrom`.
- [ ] Aligned residue count matches `alignment.n_aligned_residues`.
- [ ] Sequence identity matches `alignment.sequence_identity`.
- [ ] Every moved region's range, residue count, and displacement
      stats match the corresponding `moved_regions` entry.
- [ ] Top Cα movers match `top_ca_movers`, ordered by displacement.
- [ ] SS changes shown in Section 6 exist in `ss_changes`.
- [ ] SASA entries in Section 7 exist in `sasa_changes.top_increases`
      and `sasa_changes.top_decreases`.

## 3. Provenance markers

- [ ] Every DB-derived factual claim in Section 4 carries one of
      `(per RCSB)`, `(per UniProt <acc>)`, or `(per UniProt SPARQL)`.
- [ ] Every training-data background statement carries
      `(general background)`.
- [ ] Every background statement is tied to a specific run feature
      (a moved region, a hinge, a specific residue or displacement).
      No free-floating textbook paragraphs.
- [ ] Moved-region → named-subdomain mappings are marked
      `(inferred from run)` unless verified against a UniProt
      domain annotation, in which case `(per UniProt SPARQL)`.

## 4. No fabricated citations

- [ ] No author-year citations anywhere (regex
      `[A-Z][a-z]+\s*(&|and|et al\.?)\s*[A-Z]` matches zero).
- [ ] No fake DOI or URL references.
- [ ] No explicit journal names.

## 5. `external_metadata.json` consistency

- [ ] The file exists at `<output_dir>/external_metadata.json`.
- [ ] It validates against `schemas/external_metadata.schema.json`.
- [ ] Every entry with `fetch_ok: false` has a corresponding caveat
      either in Section 4 (graceful degradation note) or Section 9
      (Caveats).
- [ ] If all `fetch_ok` fields are false, Section 4b opens with
      `Structural context assembled from training data only; live DB
      lookup unavailable.`.

## 6. Condition variants

Based on `facts.condition`:

- [ ] If `condition == "structures_nearly_identical"`: Section 3
      reads `No moved regions identified.` and Sections 5, 6, 7 use
      the empty marker. Section 8 interprets why the structures are
      close, not motion.
- [ ] If `condition == "diffuse_motion"`: Section 3 reads `Motion
      detected but not localized to discrete regions.` and Section 5
      (Top Movers) is rendered in full. Section 8 interprets diffuse
      motion causes.
- [ ] Otherwise (drill-down): all 10 sections are populated normally.

## 7. Warnings honored

- [ ] Every string in `facts.warnings` appears in Section 9.
- [ ] Every string in `external_metadata.warnings` appears in
      Section 9.
- [ ] Every altloc residue in `facts.altloc_residues` is listed in
      Section 9.

## 8. Graceful degradation manual tests

These are not covered by automated tests. Run them when the togomcp
integration changes or when this checklist is revised.

- [ ] **Full togomcp failure.** Edit
      `examples/1ake_vs_4ake/external_metadata.json` and set every
      `fetch_ok` to `false`. Clear `structures.*.pdb_title`,
      `uniprot_mapping.pairs`, `uniprot_entries`, and
      `uniprot_sparql`. Add a top-level warning. Regenerate
      `report.md` and verify Section 4b opens with `Structural
      context assembled from training data only; live DB lookup
      unavailable.` and Sections 1–3, 5–10 remain functionally
      correct. Revert the fixture when done.
- [ ] **Partial (SPARQL-only) failure.** Edit the fixture to set
      only `uniprot_sparql.*.fetch_ok` to `false`, clear its
      `function`, `keywords`, `domains`. Regenerate the report and
      verify the UniProt function/keyword content is absent while
      PDB title and UniProt basic identity remain. Revert the
      fixture when done.

## 9. Condition-variant spot checks (P1)

Covered by automated tests only partially. When new fixtures for
`nearly_identical` or `diffuse_motion` are introduced:

- [ ] Regenerate the report for each fixture.
- [ ] Confirm the condition-variant rules in Section 6 of this
      checklist.
- [ ] Confirm the empty markers appear in the expected sections.
```

- [ ] **Step 2: Run the full test suite**

```bash
uv run --with pytest --with numpy --with jsonschema --with click pytest tests/ -q
```

Expected: all tests pass (the manual checklist is not tested automatically; this guards against side effects).

- [ ] **Step 3: Commit**

```bash
git add docs/manual_review_checklist.md
git commit -m "$(cat <<'EOF'
docs: Rewrite manual review checklist for rich report design

Replaces the old checklist (which enforced the now-reversed
no-background rule and a Japanese length target) with a new checklist
that covers the Shape 2 structural invariants, provenance markers,
external_metadata.json consistency, condition variants, and graceful
degradation manual tests.
EOF
)"
```

---

## Task 5: Regenerate `examples/1ake_vs_4ake/external_metadata.json` and `report.md`

**Rationale:** The example run is the P0 end-to-end proof that the redesign works. It also provides the snapshot that the new lint test locks.

**Files:**
- Create: `examples/1ake_vs_4ake/external_metadata.json` (new artifact)
- Modify (full rewrite): `examples/1ake_vs_4ake/report.md`
- Create: `tests/test_example_report_snapshot.py`

- [ ] **Step 1: Write the failing snapshot test**

Create `tests/test_example_report_snapshot.py`:

```python
"""Structural snapshot for examples/1ake_vs_4ake/report.md.

Does not lock prose content; only locks headings, key numeric
strings, provenance marker presence, and the absence of fake
citations or CJK characters.
"""

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_REPORT_PATH = _REPO_ROOT.joinpath("examples", "1ake_vs_4ake", "report.md")


@pytest.fixture(scope="module")
def report_text() -> str:
    return _REPORT_PATH.read_text(encoding="utf-8")


def test_report_exists(report_text: str):
    assert len(report_text) > 0


def test_h1_heading(report_text: str):
    assert report_text.startswith("# 1AKE vs 4AKE — Conformational Comparison")


@pytest.mark.parametrize(
    "heading",
    [
        "## Section 2: Global Alignment Metrics",
        "## Section 3: Moved Regions Comparison",
        "## Section 4: Structural Context",
        "## Section 5: Top C\u03b1 Movers",
        "## Section 6: Secondary Structure Changes by Region",
        "## Section 7: SASA Highlights",
        "## Section 8: Integrated Interpretation",
        "## Section 9: Caveats and Limitations",
        "## Section 10: Artifacts and Reproduction",
    ],
)
def test_section_headings_present(report_text: str, heading: str):
    assert heading in report_text, f"Missing heading: {heading}"


def test_section_order(report_text: str):
    positions = []
    for n in range(2, 11):
        match = re.search(rf"## Section {n}:", report_text)
        assert match, f"Section {n} heading missing"
        positions.append(match.start())
    assert positions == sorted(positions)


def test_key_metrics_present(report_text: str):
    assert "8.24" in report_text  # overall RMSD
    assert "214" in report_text  # n aligned
    assert "P69441" in report_text  # UniProt accession
    assert "Escherichia coli" in report_text or "E. coli" in report_text


@pytest.mark.parametrize(
    "marker",
    [
        "(per RCSB)",
        "(per UniProt",
        "(general background)",
    ],
)
def test_provenance_markers_used(report_text: str, marker: str):
    assert marker in report_text, f"Provenance marker {marker!r} missing"


def test_run_derived_marker_used(report_text: str):
    """At least one of (run-derived) or (inferred from run) must appear."""
    assert "(run-derived)" in report_text or "(inferred from run)" in report_text


def test_no_fake_citations(report_text: str):
    """No author-year citation patterns allowed.

    Matches author-year constructs like 'Müller & Schulz 1992',
    'Smith et al. (2020)', 'Jones and Brown, 1988'. Requires a
    4-digit year (19xx or 20xx) near the author tokens so that
    ordinary English prose like 'NMPbind and LID' or
    'Caveats and Limitations' does not match.
    """
    pattern = re.compile(
        r"[A-Z]\w+"
        r"(?:\s+(?:&|and)\s+[A-Z]\w+|\s+et\s*al\.?)"
        r"\s*,?\s*\(?(?:19|20)\d{2}\)?"
    )
    matches = pattern.findall(report_text)
    assert matches == [], f"Fake citation patterns found: {matches}"


def test_report_is_english(report_text: str):
    cjk = re.findall(r"[\u3000-\u9fff]", report_text)
    assert cjk == [], f"Report contains CJK characters: {cjk[:10]}"


def test_english_ratio_dominant(report_text: str):
    """ASCII-range characters should dominate (>= 90%)."""
    if not report_text:
        return
    ascii_count = sum(1 for ch in report_text if ord(ch) < 128)
    ratio = ascii_count / len(report_text)
    assert ratio >= 0.9, f"ASCII ratio too low: {ratio:.2f}"
```

- [ ] **Step 2: Run the snapshot test to verify it fails**

```bash
uv run --with pytest pytest tests/test_example_report_snapshot.py -v
```

Expected: multiple failures. The current `examples/1ake_vs_4ake/report.md` is Japanese, uses the old heading style, and has no provenance markers. Red state is expected.

- [ ] **Step 3: Fetch external metadata from togomcp**

Execute these MCP calls in order and collect the results into an
in-memory dictionary shaped like `all_ok.json`:

1. `mcp__togomcp__list_databases()` — verify success
2. `mcp__togomcp__search_pdb_entity(db="pdb", query="1AKE", limit=1)`
3. `mcp__togomcp__search_pdb_entity(db="pdb", query="4AKE", limit=1)`
4. `mcp__togomcp__togoid_convertId(ids="1AKE,4AKE", route="pdb,uniprot")`
5. For each unique UniProt accession returned (expect `P69441`):
   `mcp__togomcp__search_uniprot_entity(query="accession:P69441 AND reviewed:true", limit=1)`
6. `mcp__togomcp__get_MIE_file(dbname="uniprot")`
7. `mcp__togomcp__run_sparql(dbname="uniprot", sparql_query=<query>)`
   to fetch `function`, `keywords`, and `domains` for `P69441`. Use
   the SPARQL query grounded by the MIE file from step 6. Maximum
   two SPARQL attempts.

Record `fetch_ok`, `error`, and the raw returned content for every
call.

- [ ] **Step 4: Write `examples/1ake_vs_4ake/external_metadata.json`**

Use `Write` to save the collected metadata to
`examples/1ake_vs_4ake/external_metadata.json`. The file must conform
to `schemas/external_metadata.schema.json`.

Verify schema conformance of the newly-written example artifact with
a one-shot validation:

```bash
uv run --with jsonschema python -c "
import json
from pathlib import Path
from jsonschema import Draft202012Validator
schema = json.loads(Path('schemas/external_metadata.schema.json').read_text())
instance = json.loads(Path('examples/1ake_vs_4ake/external_metadata.json').read_text())
Draft202012Validator(schema).validate(instance)
print('ok')
"
```

Expected output: `ok`. If any `ValidationError` is raised, fix the
`external_metadata.json` to match the schema before proceeding.

- [ ] **Step 5: Regenerate `examples/1ake_vs_4ake/report.md`**

Using `Read`, load:

- `examples/1ake_vs_4ake/facts.json`
- `examples/1ake_vs_4ake/external_metadata.json`
- `templates/report_prompt.md`

Following the prompt strictly, author the English Shape 2 report and
`Write` it to `examples/1ake_vs_4ake/report.md`, overwriting the
existing Japanese file. Every hard rule from the prompt's
`## Hard rules` section must be obeyed. Run the Final self-check
block at the bottom of the prompt before saving.

- [ ] **Step 6: Run the snapshot test and the full suite**

```bash
uv run --with pytest pytest tests/test_example_report_snapshot.py -v
uv run --with pytest --with numpy --with jsonschema --with click pytest tests/ -q
```

Expected: the snapshot test passes and the full suite is green
(existing tests, schema test, prompt lint, snapshot test).

- [ ] **Step 7: Commit**

```bash
git add examples/1ake_vs_4ake/external_metadata.json \
        examples/1ake_vs_4ake/report.md \
        tests/test_example_report_snapshot.py
git commit -m "$(cat <<'EOF'
feat: Regenerate 1ake_vs_4ake example in new rich report format

Generates external_metadata.json from live togomcp fetches and
rewrites report.md in English Shape 2 format with provenance
markers. Adds a structural snapshot test that locks the skeleton
and provenance-marker presence of the example report.
EOF
)"
```

---

## Task 6: Final verification and Definition of Done

**Files:** None (verification only)

- [ ] **Step 1: Run the entire test suite**

```bash
uv run --with pytest --with numpy --with jsonschema --with click pytest tests/ -v
```

Expected: every test passes (or ChimeraX-marked tests skipped if no
ChimeraX installation). Record the final pass count.

- [ ] **Step 2: Spot-check the new example report manually**

Open `examples/1ake_vs_4ake/report.md` in an editor and walk through
the manual review checklist at `docs/manual_review_checklist.md`:

- [ ] Language and format checks (Section 1 of checklist)
- [ ] Numeric agreement with `facts.json` (Section 2)
- [ ] Provenance markers (Section 3)
- [ ] No fabricated citations (Section 4)
- [ ] `external_metadata.json` consistency (Section 5)
- [ ] Condition variant correct for drill-down (Section 6)
- [ ] Warnings honored (Section 7)

Skip Sections 8 and 9 of the checklist (graceful degradation and
condition-variant P1) for this P0 milestone.

- [ ] **Step 3: Confirm Definition of Done items from the spec**

From `docs/superpowers/specs/2026-04-09-compare-structures-rich-report-redesign.md` Section 7.7:

- [ ] `./analyze.py --in1 1AKE --in2 4AKE --out examples/1ake_vs_4ake`
      still produces `facts.json`, `aligned.cif`, `raw.json` unchanged
      (skip this check if ChimeraX is unavailable; rely on the
      untouched Python tests for regression safety).
- [ ] `examples/1ake_vs_4ake/` now contains `external_metadata.json`
      and a new-format English `report.md`.
- [ ] Manual review on the new `report.md` passes.
- [ ] `pytest tests/` is green.
- [ ] Original spec `2026-04-09-compare-structures-design.md`
      unchanged (verify with `git diff main -- docs/superpowers/specs/2026-04-09-compare-structures-design.md`).
- [ ] Memory entries for rich-report format and no-length-caps
      feedback are present in
      `~/.claude/projects/-Users-nagaet-explain-conf-skill/memory/`.

- [ ] **Step 4: Report back to the user**

Summarize in Japanese:

- Branch name and commit count
- List of files touched (new, rewritten)
- Test pass count
- Any manual-review items that need user attention
- Explicitly ask whether to push the branch and open a PR.
  **Do NOT push or open a PR without explicit user approval.**

---

## Spec coverage summary

| Spec section | Covered by task(s) |
|---|---|
| 4.1 Files changed (Rewritten) | Task 2 (prompt), Task 3 (SKILL.md), Task 4 (checklist) |
| 4.1 Files changed (Added) | Task 1 (schema, fixtures, test), Task 2 (lint test), Task 5 (snapshot test, example artifacts) |
| 4.1 Files not touched | Guarded by Task 0 baseline + Task 6 final pytest run |
| 4.2 Data flow (new step 6) | Task 3 SKILL.md rewrite + Task 5 live execution |
| 4.3 external_metadata.json schema | Task 1 |
| 4.4 Graceful degradation | Task 2 prompt Section 4b handling + Task 4 manual checklist Section 8 |
| 5.1–5.10 Report structure | Task 2 prompt rewrite + Task 5 report regeneration + snapshot test |
| 5.11 Condition variants | Task 2 prompt rewrite (drill-down P0, nearly_identical/diffuse_motion documented in prompt; P1 fixtures deferred per spec 7.6) |
| 5.12 Provenance markers | Task 2 prompt rewrite + lint test + snapshot test |
| 6.1 report_prompt.md rewrite | Task 2 |
| 6.2 SKILL.md rewrite | Task 3 |
| 6.3 external_metadata schema | Task 1 |
| 6.4 examples/1ake_vs_4ake regen | Task 5 |
| 7.1 Existing tests green | Task 0 baseline + Task 2/3/4/5/6 per-task runs |
| 7.2 Schema validation test | Task 1 |
| 7.3 Report prompt lint | Task 2 |
| 7.4 Example report snapshot | Task 5 |
| 7.5 Graceful degradation manual | Task 4 checklist Section 8 |
| 7.6 Condition variants P1 | Documented in prompt (Task 2) + checklist (Task 4); fixtures deferred |
| 7.7 Definition of Done | Task 6 |
