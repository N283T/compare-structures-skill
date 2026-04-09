# Manual Review Checklist — Generated `report.md`

Automated tests cannot validate the Japanese prose in a generated report
because LLM output is inherently variable. Use this checklist when reviewing
a new sample report during development or when diagnosing a regression.

## 1. Background-knowledge contamination

Search the report for these NG phrases (case-insensitive):

- `known to`, `known as`, `known that`
- `reported`, `has been reported`, `commonly reported`
- `typical`, `typically`, `commonly observed`
- `catalytic`, `active site`, `allosteric`
- `P-loop`, `Rossmann fold`, `Walker motif`
- 「知られている」「報告されている」「典型的な」「一般に」「触媒」「活性中心」
  「既知の」「通常」「よく観察される」

If any appear, the report violates the no-background-knowledge rule. Fix
either the prompt (templates/report_prompt.md) or the execution.

## 2. Numeric agreement with facts.json

For every numeric value in the report, check that the same value appears in
`facts.json`. Specifically verify:

- [ ] Overall RMSD matches `alignment.overall_rmsd_angstrom`
- [ ] Aligned residue count matches `alignment.n_aligned_residues`
- [ ] Sequence identity matches `alignment.sequence_identity`
- [ ] Each moved region's range matches `moved_regions[*].residue_range_label`
- [ ] Each moved region's displacement stats match
- [ ] SASA deltas quoted in the report are present in `sasa_changes`
- [ ] SS changes quoted in the report are present in `ss_changes`

## 3. Stationary-region leakage

- [ ] No residue range or residue number is mentioned that is not inside a
      `moved_regions[*].residue_range` or in `top_ca_movers`
- [ ] No chain is mentioned whose `chain_summary[*].significant_change` is
      `false`

## 4. Adaptive drill-down honored

- [ ] If `drill_down_flags.report_residue_level` is `false`, there is no
      residue-level detail section
- [ ] If `condition == "structures_nearly_identical"`, the report is short
      and says no significant change was detected
- [ ] If `condition == "diffuse_motion"`, this is explicitly stated

## 5. Warnings honored

- [ ] Every warning in `facts.json.warnings` appears in the report (short,
      factual)

## 6. Style

- [ ] All qualitative adjectives are paired with numeric values
- [ ] The report is between 600 and 1200 Japanese characters
- [ ] Tone is analytical, not speculative
