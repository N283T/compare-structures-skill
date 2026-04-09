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

Write the sections in the listed order. Sections 2 through 10 must
appear as level-2 markdown headings (`## Section N: ...`) in the
report. **Section 1 is an exception**: it is rendered as the H1 report
title plus metadata shown in its "Render as" block below, not as a
literal `## Section 1: Header` heading. Never silently omit a section;
if a section has no content under the current condition, render the
heading and an explicit empty marker `_No entries for this run._`
(except for Section 3, which has its own condition-specific markers
described in the Condition variants block).

## Section 1: Header

Render as:

```
# <ID1> vs <ID2> — Conformational Comparison

*Generated <meta.generated_at formatted as "YYYY-MM-DD HH:MM UTC"; drop seconds, microseconds, and the numeric timezone offset>*

**Headline:** <one sentence containing overall Cα RMSD in Å,
n aligned residues, sequence identity as percent, number of moved
regions, and the largest max Cα displacement in Å>.
```

## Section 2: Global Alignment Metrics

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

## Section 3: Moved Regions Comparison

A markdown table with a `Field` column plus one column per entry in
`facts.moved_regions` (so two value columns for two regions, three
for three, and so on). Rows:

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

## Section 4: Structural Context

This is the only section where DB-derived facts and training-data
background are combined. Render it as three subsections.

### Section 4a: Structure metadata

A markdown table with three columns (`Field`, `Structure 1`,
`Structure 2`) and these rows:

- `PDB ID`
- `PDB title` — `external_metadata.structures.<id>.pdb_title` when
  `fetch_ok`; otherwise `_not available_`
- `UniProt` — for each structure, find the entry in
  `external_metadata.uniprot_mapping.pairs` whose first element matches
  the PDB ID and use the second element (the UniProt accession). Write
  `_not mapped_` if the second element is `null` or the PDB ID does
  not appear in `pairs`.
- `Organism` — `external_metadata.uniprot_entries.<acc>.organism`
  when `fetch_ok`
- `Protein` — `external_metadata.uniprot_entries.<acc>.protein_names`
  when `fetch_ok`
- `Provenance` — a short phrase describing the sources, e.g.
  `per RCSB, per UniProt P69441 (via togomcp)` or
  `_DB lookup unavailable_` if every fetch failed

### Section 4b: DB-derived interpretation

One paragraph drawing only on `external_metadata.json`. Every factual
claim must carry `(per RCSB)`, `(per UniProt <acc>)`, or
`(per UniProt SPARQL)`. Cover: what are the two structures, are they
the same protein, what ligands or state do the PDB titles suggest,
and what functional annotations are available.

If all `fetch_ok` fields are false, replace this subsection with the
single sentence `Structural context assembled from training data
only; live DB lookup unavailable.`

### Section 4c: Background and motion interpretation

One or two paragraphs drawing on training-data knowledge of the
protein's architecture and dynamics. Every claim must carry
`(general background)`. Each paragraph must tie the background to a
specific feature of this run (a moved region label, a hinge residue,
a specific motion magnitude). Free-floating textbook content is
forbidden.

If you map a moved-region range to a named subdomain (e.g.
"corresponds to the LID subdomain"), mark this as
`(inferred from run)` unless `external_metadata.uniprot_sparql.<acc>.domains`
contains a domain whose residue range overlaps the moved region, in
which case mark it `(per UniProt SPARQL)`. **Overlap is defined
operationally:** parse each `domain.range` string as `start-end`
integers, parse the moved region's `residue_range` as `[region_start,
region_end]`, and the two overlap if and only if
`max(domain_start, region_start) <= min(domain_end, region_end)`.

## Section 5: Top Cα Movers

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

## Section 6: Secondary Structure Changes by Region

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

## Section 7: SASA Highlights

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

## Section 8: Integrated Interpretation

One or two paragraphs of prose synthesis. This is the only section
where run facts, DB facts, and training-data background may be woven
together in the same sentence. Every factual claim must carry its
provenance marker. Structure the synthesis to cover, in order:

- The dominant motion pattern you derived from Sections 3, 5, 6, 7.
- The structural identity of the two states from Section 4.
- The known conformational dynamics of the protein family
  (background), tied to the motion pattern above.
- Any mismatch between expectation and the run observations.

## Section 9: Caveats and Limitations

Bullets (genuine enumeration; this is the one section where a
bullet-only block is correct). Include:

- Every string in `facts.warnings`.
- Every residue in `facts.altloc_residues.structure_1` and
  `facts.altloc_residues.structure_2`, grouped by structure.
- Any boolean flag inside `drill_down_flags` that is `false` — the
  corresponding level of detail was skipped for this run. Do not look
  up `drill_down_flags.reasons[<flag>]` here: `reasons` holds entries
  only for flags that were enabled by threshold crossing, so no
  `reasons` entry exists for a false flag.
- Any `external_metadata.warnings` entry.
- Any `fetch_ok: false` in `external_metadata` that materially
  affected the report.

If none of these bullets have content, write `_No caveats for this
run._`.

## Section 10: Artifacts and Reproduction

Bullets listing the artifacts in the run directory, then the
reproduction command:

- `aligned.cif` — superposed structure
- `facts.json` — computed run facts
- `external_metadata.json` — DB lookup snapshot
- `raw.json` — raw ChimeraX output
- Reproduction: `./analyze.py --in1 <id1> --in2 <id2> --out <dir>`

## Condition variants

The condition is indicated by `facts.condition`. Handle it as follows:

### drill-down (default)

Use when `condition` is null or unset. If `facts.moved_regions` is
non-empty, render all 10 sections as specified above with no special
handling. If `facts.moved_regions` is unexpectedly empty while
`condition` is still null, keep the drill-down variant but let
Section 3's own empty-table rule take over (literal sentence
`No discrete moved regions identified.`); Sections 5, 6, 7 then use
the generic `_No entries for this run._` marker if their underlying
facts are also empty.

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
      with the appropriate empty marker. Section 3 has its own
      condition-specific sentences (`No discrete moved regions
      identified.`, `No moved regions identified.`, or `Motion
      detected but not localized to discrete regions.`); all other
      sections use the generic `_No entries for this run._` marker.
- [ ] The report's depth reflects the amount of data in this run and
      is not artificially padded or compressed.
