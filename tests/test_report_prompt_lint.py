"""Structural lint for templates/report_prompt.md.

Does not check prose content; only that the required structural
elements (hard rules, provenance markers, section skeleton, final
self-check, per-section empty-handling) are present.

This guard matters because the prompt is a plain-text contract that
is not otherwise exercised by the Python pipeline. Without this lint,
a careless edit could silently delete a provenance marker or hard
rule and no runtime check would catch it until a manual review.
"""

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PROMPT_PATH = _REPO_ROOT.joinpath("templates", "report_prompt.md")

# CJK range covers Hiragana, Katakana, CJK Unified Ideographs, and CJK
# symbols/punctuation (U+3000-U+9FFF) plus halfwidth katakana and
# fullwidth Latin (U+FF00-U+FFEF). The broadened range catches
# easy-to-miss drift modes such as fullwidth punctuation pasted from
# a Japanese editor.
_CJK_PATTERN = re.compile(r"[\u3000-\u9fff\uff00-\uffef]")


@pytest.fixture(scope="module")
def prompt_text() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def test_prompt_file_exists(prompt_text: str):
    assert len(prompt_text) > 0, "report_prompt.md is empty"


def test_prompt_is_english(prompt_text: str):
    """No CJK or fullwidth characters allowed.

    The report is authored in English (decision recorded in the memory
    feedback_scientific_reports_rich_format.md). Any CJK or fullwidth
    character slipping into the prompt typically indicates accidental
    reversion to an older Japanese version.
    """
    cjk = _CJK_PATTERN.findall(prompt_text)
    assert cjk == [], f"Prompt contains CJK/fullwidth characters: {cjk[:10]}"


def test_six_hard_rules_present(prompt_text: str):
    """The hard-rules section must contain exactly 6 numbered items.

    Guards against a drift that silently adds or removes a rule. The
    count is intentionally strict — any edit that legitimately changes
    the rule count must update this test.
    """
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
    """Every provenance marker must appear in the prompt.

    Presence anywhere in the file is a coarse check; the stricter
    table-row check is test_provenance_marker_in_table_row below.
    """
    assert marker in prompt_text, f"Provenance marker {marker!r} missing from prompt"


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
def test_provenance_marker_in_table_row(prompt_text: str, marker: str):
    """Every provenance marker must appear inside a markdown table row.

    Presence alone is insufficient: a future edit could convert the
    provenance table into prose while leaving all marker literals
    elsewhere, passing the coarse presence check but destroying the
    table form the readers rely on. This test locks the table form.
    """
    marker_in_table_row = any(
        marker in line and line.count("|") >= 2 and line.lstrip().startswith("|")
        for line in prompt_text.split("\n")
    )
    assert marker_in_table_row, f"Provenance marker {marker!r} is not inside any markdown table row"


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
    """Each of the 10 section labels must appear in the prompt body."""
    assert heading in prompt_text, f"Missing section heading: {heading}"


def test_section_order(prompt_text: str):
    """Sections 1-10 must appear in the prompt in strictly increasing order."""
    positions = []
    for n in range(1, 11):
        match = re.search(rf"Section {n}:", prompt_text)
        assert match, f"Section {n} header missing"
        positions.append(match.start())
    assert positions == sorted(positions), f"Sections are out of order: {positions}"


def test_condition_variants_documented(prompt_text: str):
    """All three condition variants must be named in the prompt."""
    for label in ("drill-down", "nearly_identical", "diffuse_motion"):
        assert label in prompt_text, f"Condition variant '{label}' not documented"


def test_empty_marker_string(prompt_text: str):
    """The literal generic empty-section marker must be present."""
    assert "_No entries for this run._" in prompt_text


@pytest.mark.parametrize(
    "section_heading,expected_empty_marker",
    [
        ("## Section 3:", "No discrete moved regions identified."),
        ("## Section 6:", "_No entries for this run._"),
        ("## Section 7:", "_No entries for this run._"),
    ],
)
def test_section_has_empty_handling(
    prompt_text: str, section_heading: str, expected_empty_marker: str
):
    """Each section with an empty-data path must have a local fallback.

    The condition-variants block at the bottom of the prompt is not
    a substitute for per-section handling: a model reading a section
    in isolation needs to see its own empty-data instruction. This
    test pins the local instruction so drift cannot remove it while
    leaving only the distant condition-variants reference.
    """
    start = prompt_text.find(section_heading)
    assert start >= 0, f"Section heading not found: {section_heading}"
    next_section_match = re.search(r"\n## ", prompt_text[start + 1 :])
    end = start + 1 + next_section_match.start() if next_section_match else len(prompt_text)
    section_block = prompt_text[start:end]
    assert expected_empty_marker in section_block, (
        f"Section {section_heading} missing empty-handling instruction '{expected_empty_marker}'"
    )


def test_final_self_check_present(prompt_text: str):
    """The Final self-check section must exist.

    The `or` tolerance here accepts sentence-case and title-case
    spellings so minor casing drift does not break the test.
    """
    assert "## Final self-check" in prompt_text or "## Final Self-Check" in prompt_text


@pytest.mark.parametrize(
    "phrase",
    [
        "Every numerical value",
        "provenance marker",
        "(general background)",
        "No author-year",
        "No CJK characters",
    ],
)
def test_self_check_item_present(prompt_text: str, phrase: str):
    """The Final self-check must enumerate each of these load-bearing checks.

    Presence of the Final self-check header is not sufficient; a
    future edit could empty the block or drop individual items. This
    test locks each critical self-review item.
    """
    self_check_start = prompt_text.find("## Final self-check")
    if self_check_start < 0:
        self_check_start = prompt_text.find("## Final Self-Check")
    assert self_check_start >= 0, "Missing Final self-check section"
    self_check_block = prompt_text[self_check_start:]
    assert phrase in self_check_block, f"Final self-check missing phrase: {phrase!r}"


def test_general_background_marker_referenced(prompt_text: str):
    """The prompt must instruct the model to mark background explicitly."""
    assert prompt_text.count("(general background)") >= 2
