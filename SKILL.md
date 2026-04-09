---
name: compare-structures
description: Compare two protein structures (apo/holo, open/closed, WT/mutant, etc.) using ChimeraX and explain the conformational change in Japanese. Use when the user provides two PDB IDs or two structure files and asks for a structural comparison or conformational analysis.
allowed-tools: Read, Write, Bash, mcp__togomcp__*
---

# compare-structures

Compare two protein structures via headless ChimeraX and produce a Japanese
analytical report grounded strictly in computed facts.

## Workflow

1. **Extract inputs from the user request.** Two structures, each either a
   4-character PDB ID (e.g. `1AKE`) or a path to a local `.pdb`/`.cif`/`.mmcif`
   file. If the request is ambiguous, ask the user for clarification before
   proceeding.

2. **Decide an output directory.** Use a timestamp-suffixed name under `runs/`
   in the repo root (or the caller's current working directory if the repo is
   not present):
   ```
   runs/<id1>_vs_<id2>_<YYYYmmdd_HHMMSS>/
   ```

3. **Run the analysis pipeline.** Use `Bash` to invoke `analyze.py` from this
   skill's directory:
   ```bash
   "<skill_dir>/analyze.py" \
     --in1 "<in1>" --in2 "<in2>" \
     --out "<output_dir>"
   ```
   Do not set `--timeout` unless the user asks — the default (30 minutes) is
   intended for most structures.

4. **Check the exit status.**
   - **Exit 0:** continue to step 5.
   - **Non-zero:** read `<output_dir>/error.json` and summarize the failure to
     the user in 2-3 Japanese sentences. Do not continue to step 5. Do not
     paste stack traces into chat — refer the user to the error.json path
     instead.

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

## Failure Modes

| Exit code | Meaning | Action |
|---|---|---|
| 0 | Success | Proceed to report writing |
| 2 | Input validation failed | Summarize the validation error to the user |
| 3 | ChimeraX subprocess failed / timed out | Summarize, point at `error.json` |
| 4 | Missing `raw.json` after ChimeraX ran | Report a pipeline bug (rare) |
| 5 | Post-processing failed | Summarize, point at `error.json` |

## Dependencies

- ChimeraX must be installed. The script looks at `$CHIMERAX_PATH` first,
  then the first `chimerax` on `PATH`.
- `uv` must be installed (the `analyze.py` shebang uses
  `#!/usr/bin/env -S uv run --script`).
