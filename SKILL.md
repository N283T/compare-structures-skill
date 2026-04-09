---
name: compare-structures
description: Compare two protein structures (apo/holo, open/closed, WT/mutant, etc.) using ChimeraX and explain the conformational change in Japanese. Use when the user provides two PDB IDs or two structure files and asks for a structural comparison or conformational analysis.
allowed-tools: Read, Write, Bash
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

6. **Write the report.** Following the prompt in `report_prompt.md` strictly
   (every hard constraint, in particular the no-background-knowledge rule),
   use `Write` to create `<output_dir>/report.md`.

7. **Reply to the user.** 2-5 lines summarizing:
   - The headline metrics (overall RMSD, number of moved regions)
   - Paths to the artifacts (`report.md`, `aligned.cif`, `facts.json`)
   Example:
   > 1AKE と 4AKE の比較が完了しました。全体 Cα RMSD は 5.53 Å、動いた領域は
   > A/30-59 と A/118-167 の 2 箇所。詳細は `runs/1AKE_vs_4AKE_20260409_124530/report.md`
   > を参照してください。

## Hard Constraints

- **No background knowledge in the report.** The prompt in
  `templates/report_prompt.md` forbids literature context, mechanistic
  interpretation, and named-entity priors. Follow it literally.
- **Do not skip the pipeline.** Never write a report without running
  `analyze.py` — the report must reflect the actual `facts.json` for this run.
- **Do not modify `facts.json`.** It is a generated artifact.

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
