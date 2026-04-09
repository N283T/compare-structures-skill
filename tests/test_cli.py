"""Tests for compare_structures.cli — end-to-end wiring with mocked ChimeraX."""

import json
from pathlib import Path
from unittest.mock import patch

from compare_structures import cli


def _fake_chimerax_runner_impl(raw_payload, aligned_payload=b"data_test\n"):
    def _run(chimerax_executable, script_path, script_args, timeout_seconds):
        # argv order from cli.main: in1, in2, raw_out, aligned_out, chain1, chain2
        raw_out = Path(script_args[2])
        aligned_out = Path(script_args[3])
        raw_out.write_text(json.dumps(raw_payload))
        aligned_out.write_bytes(aligned_payload)
        import subprocess

        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    return _run


def _minimal_raw(in1_id="1TST", in2_id="2TST"):
    res_1 = [
        {
            "chain_id": "A",
            "res_num": i,
            "res_name": "ALA",
            "ca_coord": [0.0, 0.0, 0.0],
            "sasa": 100.0,
            "ss_type": "C",
            "altloc_ids": [],
            "max_occupancy": 1.0,
        }
        for i in range(1, 11)
    ]
    res_2 = [
        {
            "chain_id": "A",
            "res_num": i,
            "res_name": "ALA",
            "ca_coord": [0.1, 0.0, 0.0],
            "sasa": 100.0,
            "ss_type": "C",
            "altloc_ids": [],
            "max_occupancy": 1.0,
        }
        for i in range(1, 11)
    ]
    return {
        "input1": {"id": in1_id, "source": "pdb_id", "model_id": 1},
        "input2": {"id": in2_id, "source": "pdb_id", "model_id": 2},
        "matchmaker": {
            "reference_model": 1,
            "moved_model": 2,
            "full_rmsd": 0.1,
            "final_rmsd": 0.05,
            "n_full_pairs": 10,
            "n_final_pairs": 10,
            "per_chain": [],
        },
        "chains": [
            {"chain_id": "A", "model": 1, "residues": res_1},
            {"chain_id": "A", "model": 2, "residues": res_2},
        ],
        "chimerax_version": "1.11.1",
        "schema_version": "1.0",
    }


class TestCliMain:
    def test_successful_end_to_end(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CHIMERAX_PATH", str(tmp_path / "chimerax"))
        (tmp_path / "chimerax").write_text("")
        raw = _minimal_raw()
        out = tmp_path / "runs" / "out"
        with patch(
            "compare_structures.cli.run_chimerax_script",
            side_effect=_fake_chimerax_runner_impl(raw),
        ):
            exit_code = cli.main(
                [
                    "--in1",
                    "1TST",
                    "--in2",
                    "2TST",
                    "--out",
                    str(out),
                ],
                standalone_mode=False,
            )
        assert exit_code == 0
        assert (out / "raw.json").is_file()
        assert (out / "facts.json").is_file()
        assert (out / "aligned.cif").is_file()
        facts = json.loads((out / "facts.json").read_text())
        assert facts["condition"] == "structures_nearly_identical"

    def test_invalid_pdb_writes_error_json(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CHIMERAX_PATH", str(tmp_path / "chimerax"))
        (tmp_path / "chimerax").write_text("")
        out = tmp_path / "runs" / "out"
        exit_code = cli.main(
            [
                "--in1",
                "xxx",  # not a 4-char PDB id and not a file
                "--in2",
                "1TST",
                "--out",
                str(out),
            ],
            standalone_mode=False,
        )
        assert exit_code != 0
        err = json.loads((out / "error.json").read_text())
        assert err["stage"] == "validation"
        assert "PDB ID" in err["message"] or "pdb id" in err["message"].lower()

    def test_chimerax_failure_writes_error_json(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CHIMERAX_PATH", str(tmp_path / "chimerax"))
        (tmp_path / "chimerax").write_text("")
        from compare_structures.chimerax_runner import ChimeraxRunError

        out = tmp_path / "runs" / "out"

        def _raise(**kwargs):
            raise ChimeraxRunError("boom", stderr_tail="traceback...")

        with patch("compare_structures.cli.run_chimerax_script", side_effect=_raise):
            exit_code = cli.main(
                [
                    "--in1",
                    "1TST",
                    "--in2",
                    "2TST",
                    "--out",
                    str(out),
                ],
                standalone_mode=False,
            )
        assert exit_code != 0
        err = json.loads((out / "error.json").read_text())
        assert err["stage"] == "chimerax_script"
        assert err["stderr_tail"] == "traceback..."

    def test_post_processing_failure_writes_error_json(self, tmp_path, monkeypatch):
        """Post-processing failure writes error.json with stage=analyze_post."""
        monkeypatch.setenv("CHIMERAX_PATH", str(tmp_path / "chimerax"))
        (tmp_path / "chimerax").write_text("")
        # Feed the fake runner a payload that fails facts_builder (missing 'matchmaker' key).
        bad_raw = {
            "input1": {"id": "1TST", "source": "pdb_id", "model_id": 1},
            "input2": {"id": "2TST", "source": "pdb_id", "model_id": 2},
            # Deliberately omit 'matchmaker' and 'chains' so build_facts blows up.
        }
        out = tmp_path / "runs" / "out"
        with patch(
            "compare_structures.cli.run_chimerax_script",
            side_effect=_fake_chimerax_runner_impl(bad_raw),
        ):
            exit_code = cli.main(
                [
                    "--in1",
                    "1TST",
                    "--in2",
                    "2TST",
                    "--out",
                    str(out),
                ],
                standalone_mode=False,
            )
        assert exit_code == 5
        err = json.loads((out / "error.json").read_text())
        assert err["stage"] == "analyze_post"
