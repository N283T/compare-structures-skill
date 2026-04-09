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
