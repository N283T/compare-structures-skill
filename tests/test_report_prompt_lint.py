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
        "(per UniProt <acc>)",
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
    assert positions == sorted(positions), f"Sections are out of order: {positions}"


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
