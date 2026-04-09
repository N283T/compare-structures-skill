"""click-based CLI entry point for analyze.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from .chimerax_runner import (
    ChimeraxRunError,
    ChimeraxTimeoutError,
    run_chimerax_script,
)
from .errors import write_error
from .facts_builder import build_facts
from .thresholds import DEFAULT_TIMEOUT_SECONDS
from .validators import (
    InputValidationError,
    resolve_chimerax_executable,
    validate_input,
)


@click.command()
@click.option("--in1", "in1_arg", required=True, help="First structure (PDB ID or file path)")
@click.option("--in2", "in2_arg", required=True, help="Second structure (PDB ID or file path)")
@click.option("--out", "out_arg", required=True, type=click.Path(), help="Output directory")
@click.option(
    "--timeout",
    "timeout_arg",
    default=DEFAULT_TIMEOUT_SECONDS,
    type=int,
    help=f"ChimeraX subprocess timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS})",
)
@click.option(
    "--chain1",
    "chain1_arg",
    default="",
    help="Restrict matchmaker on structure 1 to this chain ID (default: all chains)",
)
@click.option(
    "--chain2",
    "chain2_arg",
    default="",
    help="Restrict matchmaker on structure 2 to this chain ID (default: all chains)",
)
def _cli_command(
    in1_arg: str,
    in2_arg: str,
    out_arg: str,
    timeout_arg: int,
    chain1_arg: str,
    chain2_arg: str,
) -> None:
    code = _run(in1_arg, in2_arg, out_arg, timeout_arg, chain1_arg, chain2_arg)
    sys.exit(code)


def _run(
    in1: str,
    in2: str,
    out: str,
    timeout: int,
    chain1: str = "",
    chain2: str = "",
) -> int:
    output_dir = Path(out).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: validation.
    try:
        norm_1 = validate_input(in1)
        norm_2 = validate_input(in2)
        chimerax_exe = resolve_chimerax_executable()
    except InputValidationError as e:
        write_error(
            output_dir,
            error_type="validation",
            message=str(e),
            stage="validation",
        )
        click.echo(f"validation failed: {e}", err=True)
        return 2

    # Stage 2: ChimeraX subprocess.
    raw_out = output_dir / "raw.json"
    aligned_out = output_dir / "aligned.cif"
    script_path = Path(__file__).resolve().parent.parent / "chimerax_script.py"

    def _arg_for(norm: dict, original: str) -> str:
        if norm["source"] == "pdb_id":
            return norm["id"]
        return str(norm["path"])

    try:
        run_chimerax_script(
            chimerax_executable=chimerax_exe,
            script_path=script_path,
            script_args=[
                _arg_for(norm_1, in1),
                _arg_for(norm_2, in2),
                str(raw_out),
                str(aligned_out),
                chain1,
                chain2,
            ],
            timeout_seconds=timeout,
        )
    except ChimeraxTimeoutError as e:
        write_error(
            output_dir,
            error_type="chimerax_timeout",
            message=str(e),
            stage="chimerax_script",
            stderr_tail=e.stderr_tail,
        )
        click.echo(f"chimerax timeout: {e}", err=True)
        return 3
    except ChimeraxRunError as e:
        write_error(
            output_dir,
            error_type="chimerax_failed",
            message=str(e),
            stage="chimerax_script",
            stderr_tail=e.stderr_tail,
        )
        click.echo(f"chimerax failed: {e}", err=True)
        return 3

    if not raw_out.is_file():
        write_error(
            output_dir,
            error_type="missing_raw_output",
            message="chimerax_script.py did not produce raw.json",
            stage="chimerax_script",
        )
        return 4

    # Stage 3: post-processing.
    try:
        raw = json.loads(raw_out.read_text())
        build_facts(raw, output_dir)
    except Exception as e:  # noqa: BLE001
        write_error(
            output_dir,
            error_type=type(e).__name__,
            message=str(e),
            stage="analyze_post",
        )
        click.echo(f"post-processing failed: {e}", err=True)
        return 5

    click.echo(f"analysis complete: {output_dir}")
    return 0


def main(argv: list[str] | None = None, standalone_mode: bool = True) -> int:
    """Entry point usable both as CLI and from tests.

    When ``standalone_mode`` is False, click parses the args into a context and
    we call ``_run`` directly, returning its exit code instead of calling
    ``sys.exit``.
    """
    if standalone_mode:
        _cli_command.main(args=argv, standalone_mode=True)
        return 0  # unreachable — click will sys.exit

    ctx = _cli_command.make_context("compare-structures", list(argv or []))
    with ctx:
        return _run(
            in1=ctx.params["in1_arg"],
            in2=ctx.params["in2_arg"],
            out=ctx.params["out_arg"],
            timeout=ctx.params["timeout_arg"],
            chain1=ctx.params["chain1_arg"],
            chain2=ctx.params["chain2_arg"],
        )
