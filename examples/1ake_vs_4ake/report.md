# 1AKE vs 4AKE — Conformational Comparison

*Generated 2026-04-09 05:55 UTC*

**Headline:** Overall Cα RMSD 8.24 Å over 214 aligned residues (100.0 % identity); two moved regions localized to A/32–70 and A/117–166, with the largest max Cα displacement of 24.71 Å.

## Section 2: Global Alignment Metrics

| Metric | Value |
|---|---|
| Alignment method | matchmaker |
| Reference / Moved structure | 1AKE / 4AKE |
| Overall Cα RMSD | 8.24 Å |
| Refined RMSD | 1.083 Å |
| Aligned residues | 214 |
| Sequence identity | 100.0 % |
| Chain A displacement (mean / median / p95 / max) | 5.31 / 1.73 / 19.39 / 24.71 Å |
| Total \|ΔSASA\| | 3672.18 Å² |
| Moved regions | 2 |

## Section 3: Moved Regions Comparison

| Field | Region 1 | Region 2 |
|---|---|---|
| Residue range | A/32–70 | A/117–166 |
| n residues | 39 | 50 |
| Mean / max Cα displacement | 9.05 / 18.02 Å | 12.80 / 24.71 Å |
| Estimated rotation | 42.02° | 49.13° |
| Estimated translation | 42.80 Å | 36.12 Å |
| Hinge candidate residues | 31, 71 | 116, 167 |

Region 2 is the dominant mover: its mean Cα displacement (12.80 Å) is 41 % larger than Region 1's (9.05 Å), its max displacement (24.71 Å) is 37 % larger than Region 1's (18.02 Å), and its estimated rotation (49.13°) is only 7° greater than Region 1's (42.02°), indicating that both regions undergo large, rigid-body-like rotations of comparable angular magnitude but with Region 2 sweeping a much longer arc. The estimated translations tell a complementary story: Region 1 translates 42.80 Å while Region 2 translates 36.12 Å, so Region 1 moves somewhat further in absolute terms despite its smaller mean displacement, suggesting the two regions pivot around distinct hinges rather than moving in concert. The hinge candidate residues (31, 71 for Region 1; 116, 167 for Region 2) are separated by roughly 45 residues and do not coincide, consistent with two independent rigid-body motions.

## Section 4: Structural Context

### Section 4a: Structure metadata

| Field | Structure 1 (1AKE) | Structure 2 (4AKE) |
|---|---|---|
| PDB ID | 1AKE | 4AKE |
| PDB title | "STRUCTURE OF THE COMPLEX BETWEEN ADENYLATE KINASE FROM ESCHERICHIA COLI AND THE INHIBITOR AP5A REFINED AT 1.9 ANGSTROMS RESOLUTION: A MODEL FOR A CATALYTIC TRANSITION STATE" | "ADENYLATE KINASE" |
| UniProt | P69441 | P69441 |
| Organism | *Escherichia coli* (strain K12) | *Escherichia coli* (strain K12) |
| Protein | Adenylate kinase (EC 2.7.4.3) | Adenylate kinase (EC 2.7.4.3) |
| Provenance | per RCSB, per UniProt P69441 (via togomcp) | per RCSB, per UniProt P69441 (via togomcp) |

### Section 4b: DB-derived interpretation

Both structures map to UniProt accession P69441 (per togomcp togoid_convertId), confirming that 1AKE and 4AKE are two states of the same *E. coli* adenylate kinase and not variants, mutants, or homologues (per UniProt P69441). The 1AKE title explicitly states it is a complex with the bi-substrate inhibitor AP5A, refined at 1.9 Å, and describes the entry as "a model for a catalytic transition state" (per RCSB). The 4AKE title is sparse — simply "ADENYLATE KINASE" — and carries no explicit ligand annotation (per RCSB), which is consistent with a ligand-free form but cannot be confirmed from the title alone. Functionally, the enzyme catalyzes the reversible transfer of the terminal phosphate group between ATP and AMP (EC 2.7.4.3) and plays an important role in cellular energy homeostasis and adenine nucleotide metabolism (per UniProt SPARQL). UniProt P69441 also annotates a three-domain architecture — a large central CORE domain and two small peripheral domains, NMPbind and LID — that undergo movements during catalysis, with the LID closing over the site of phosphoryl transfer upon ATP binding (per UniProt SPARQL).

### Section 4c: Background and motion interpretation

Adenylate kinase is one of the most-studied examples of induced-fit domain closure in enzymology (general background); the open (substrate-free) and closed (substrate- or inhibitor-bound) forms differ by large rigid-body motions of the NMP-binding and LID subdomains around hinges at the CORE interface. In this run, the two moved regions identified by the ChimeraX analysis correspond directly to the UniProt-annotated NMPbind (residues 30–59) and LID (residues 122–159) regions: moved region 1 (A/32–70) covers and slightly extends beyond NMPbind, and moved region 2 (A/117–166) covers LID almost exactly (per UniProt SPARQL). The ChimeraX-derived hinge candidate residues for Region 2 are 116 and 167, bracketing the UniProt LID range 122–159 — a one-residue precision match on the C-terminal side and a five-residue offset on the N-terminal side, consistent with the hinges sitting just outside the moving subdomain (inferred from run, cross-checked against per UniProt SPARQL domain ranges). The direction of the transition in this comparison (1AKE → 4AKE) is therefore from the closed/inhibitor-bound state toward a more open state: 1AKE has an AP5A ligand clamping LID and NMPbind together against CORE (per RCSB), while the 24.71 Å max Cα displacement and 49° rotation observed for the LID region (run-derived) are the signature of LID swinging away from that closed position.

## Section 5: Top Cα Movers

| Rank | Res num | Res name | Cα disp (Å) | In region | SS change | ΔSASA (Å²) |
|---|---|---|---|---|---|---|
| 1 | 149 | THR | 24.71 | A/117–166 | — | — |
| 2 | 150 | GLY | 24.33 | A/117–166 | — | — |
| 3 | 148 | VAL | 23.38 | A/117–166 | — | — |
| 4 | 151 | GLU | 22.87 | A/117–166 | E→C | — |
| 5 | 147 | ASP | 21.52 | A/117–166 | — | — |
| 6 | 145 | LYS | 20.65 | A/117–166 | E→C | — |
| 7 | 152 | GLU | 20.58 | A/117–166 | E→C | — |
| 8 | 142 | VAL | 20.55 | A/117–166 | — | — |
| 9 | 146 | ASP | 20.27 | A/117–166 | E→C | — |
| 10 | 128 | PRO | 20.13 | A/117–166 | — | — |

Every one of the top ten Cα movers is contained within Region 2 (A/117–166), and nine of the ten fall within the contiguous stretch 142–152, placing the peak of the motion near the middle of the LID range rather than at its edges. Residues 145, 146, 151, and 152 additionally undergo an E→C secondary-structure transition, indicating that the β-strand character of this stretch is lost along with the rigid-body swing.

## Section 6: Secondary Structure Changes by Region

#### Region 1 (A/32–70)

| Res num | Res name | Before | After |
|---|---|---|---|
| 41 | SER | H | C |
| 42 | GLY | H | C |
| 44 | GLU | C | H |
| 45 | LEU | C | H |
| 46 | GLY | C | H |
| 47 | LYS | C | H |
| 48 | GLN | C | H |
| 55 | ALA | H | C |
| 56 | GLY | H | C |
| 60 | THR | H | C |

Region 1 undergoes a rearrangement of α-helix boundaries rather than wholesale loss of secondary structure: residues 41–42 and 55–60 exit the helical state (H→C), while residues 44–48 gain helical character (C→H). The net effect is a shift of a short helix by roughly three residues along the chain while keeping the total helical content nearly constant.

#### Region 2 (A/117–166)

| Res num | Res name | Before | After |
|---|---|---|---|
| 122 | GLY | E | C |
| 135 | VAL | E | C |
| 144 | GLY | E | C |
| 145 | LYS | E | C |
| 146 | ASP | E | C |
| 151 | GLU | E | C |
| 152 | GLU | E | C |
| 153 | LEU | E | C |
| 154 | THR | E | C |
| 160 | GLN | H | C |

Region 2 shows a different pattern: nine of ten transitions are E→C, indicating that β-strand structure is lost across the entire LID range. The disrupted strands cluster at residues 122, 135, and 144–154 — three separate β-strand segments all collapsing to coil simultaneously. Combined with the 24.71 Å maximum Cα displacement on residue 149, this is the signature of a rigid β-sheet in the closed state being disrupted wholesale as LID swings open (run-derived).

#### Outside moved regions

| Res num | Res name | Before | After |
|---|---|---|---|
| 1 | MET | E | C |
| 7 | GLY | C | E |
| 12 | GLY | H | C |
| 25 | GLY | H | C |
| 30 | SER | H | C |
| 75 | GLU | C | H |
| 76 | ASP | C | H |
| 77 | CYS | C | H |
| 89 | THR | H | C |
| 99 | ALA | H | C |
| 104 | ASP | E | C |
| 113 | ASP | C | H |
| 114 | GLU | C | H |
| 176 | ALA | C | H |
| 188 | ALA | H | C |
| 198 | GLY | E | C |
| 201 | PRO | H | C |
| 214 | GLY | H | C |

Eighteen additional SS transitions occur outside the two moved regions, distributed broadly across the CORE domain and the chain termini. Most are localized single-residue flips (H↔C or C↔E) at the edges of secondary-structure elements rather than full-element collapses, consistent with minor boundary jitter in the CORE region while the two moving subdomains carry the bulk of the conformational change.

## Section 7: SASA Highlights

**Top increases**

| Res num | Res name | ΔSASA (Å²) | In region |
|---|---|---|---|
| 18 | GLN | +110.38 | — |
| 173 | GLN | +102.74 | — |
| 141 | LYS | +94.71 | A/117–166 |
| 58 | LEU | +89.00 | A/32–70 |
| 169 | VAL | +79.63 | — |
| 202 | VAL | +76.19 | — |
| 137 | PHE | +72.98 | A/117–166 |
| 40 | LYS | +72.85 | A/32–70 |
| 206 | ARG | +72.75 | — |
| 132 | VAL | +69.86 | A/117–166 |

**Top decreases**

| Res num | Res name | ΔSASA (Å²) | In region |
|---|---|---|---|
| 79 | ASN | -38.27 | — |
| 102 | ASN | -35.56 | — |
| 97 | LYS | -33.97 | — |

SASA change is overwhelmingly positive: the ten largest increases are all in the +69 to +110 Å² range, while the three largest decreases max out at only −38 Å². Four of the ten top-increase residues (141, 137, 132, and the LID-flanking 169) lie within or immediately adjacent to Region 2 (A/117–166), and two (58 and 40) lie within Region 1 (A/32–70), so at least six of the ten largest surface exposures are produced by the LID and NMPbind motions themselves. The remaining four — residues 18, 173, 202, and 206 — lie in the CORE and at the C-terminal tail, and their exposure presumably reflects the loss of the closed-form packing interface between CORE and the now-departed LID/NMPbind subdomains (inferred from run). The total |ΔSASA| of 3672.18 Å² confirms a global, not local, exposure change (run-derived).

## Section 8: Integrated Interpretation

The evidence across Sections 2–7 converges on a single, internally consistent picture. The ChimeraX analysis identified two moved regions (A/32–70 and A/117–166) that, by the UniProt P69441 region annotations (per UniProt SPARQL), correspond to the NMPbind (30–59) and LID (122–159) subdomains of *E. coli* adenylate kinase. Region 2 is the dominant mover: max Cα displacement 24.71 Å at THR149, 49° rotation, extensive E→C secondary-structure loss across residues 122, 135, and 144–154, and the top ten Cα movers all falling within its range (run-derived). Region 1 shows a smaller but substantial motion (max 18.02 Å, 42° rotation) with a localized helix-boundary rearrangement rather than wholesale structural loss (run-derived). The 1AKE entry is explicitly a complex with the AP5A bi-substrate inhibitor — a transition-state mimic that clamps LID and NMPbind over CORE (per RCSB) — while the 4AKE title carries no ligand annotation (per RCSB). Taken together with the 3672.18 Å² net SASA increase and the LID β-sheet collapse, the transition from 1AKE to 4AKE captures adenylate kinase going from the closed, inhibitor-bound, catalytically competent state to a more open state with LID and NMPbind swung away from CORE.

This is the classical induced-fit open-to-closed transition of adenylate kinase, observed here in reverse because matchmaker is reporting 1AKE as the reference and 4AKE as the moved structure (general background; ordering inferred from `facts.alignment.reference` = 1AKE and `facts.alignment.moved` = 4AKE). The 24.71 Å LID swing is at the upper end of what is typically seen between AK open and closed crystal forms (general background), consistent with 1AKE being a particularly tight transition-state mimic complex and 4AKE being a relatively open apo-like form. No aspect of the run contradicts this interpretation: there is no disordered-region signal in the top movers, no indication of crystal-packing-only motion (the motion is too large and too domain-localized), and the pairing of NMPbind and LID motion rather than motion in only one subdomain matches the coupled two-domain closure expected for this enzyme family (general background, tied to Region 1 + Region 2 pair from run).

## Section 9: Caveats and Limitations

- Structure 1 (1AKE) contains one altloc residue: A/167 ARG (max occupancy 1.00). Residue 167 is one of the hinge candidates for Region 2 (the LID), so the altloc conformation at this position may modulate the apparent hinge geometry for that region; the analysis used the primary conformer.
- Structure 2 (4AKE) contains no altloc residues.
- `facts.warnings` is empty; no pipeline-level warnings were raised.
- `external_metadata.warnings` is empty; all togomcp fetches (list_databases, search_pdb_entity ×2, togoid_convertId, search_uniprot_entity, get_MIE_file, run_sparql) returned successfully.
- All three `drill_down_flags` (`report_residue_level`, `report_sasa`, `report_ss_changes`) are `true`, so no detail section was suppressed.
- `keywords` in `external_metadata.uniprot_sparql.P69441` is empty because the SPARQL budget was spent on the function / region / binding-site query rather than a separate keyword fetch; this does not affect the substantive interpretation because the function and domain annotations are already present.

## Section 10: Artifacts and Reproduction

- `aligned.cif` — superposed structure (matchmaker reference 1AKE, moved 4AKE)
- `facts.json` — computed run facts (schema version 1.0)
- `external_metadata.json` — togomcp DB lookup snapshot
- `raw.json` — raw ChimeraX output
- Reproduction: `./analyze.py --in1 1AKE --in2 4AKE --out examples/1ake_vs_4ake`
