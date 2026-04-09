"""Structural snapshot for examples/1ake_vs_4ake/report.md.

Does not lock prose content; only locks headings, key numeric
strings, provenance marker presence, and the absence of fake
citations or CJK characters.
"""

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_REPORT_PATH = _REPO_ROOT.joinpath("examples", "1ake_vs_4ake", "report.md")


@pytest.fixture(scope="module")
def report_text() -> str:
    return _REPORT_PATH.read_text(encoding="utf-8")


def test_report_exists(report_text: str):
    assert len(report_text) > 0


def test_h1_heading(report_text: str):
    assert report_text.startswith("# 1AKE vs 4AKE — Conformational Comparison")


@pytest.mark.parametrize(
    "heading",
    [
        "## Section 2: Global Alignment Metrics",
        "## Section 3: Moved Regions Comparison",
        "## Section 4: Structural Context",
        "## Section 5: Top C\u03b1 Movers",
        "## Section 6: Secondary Structure Changes by Region",
        "## Section 7: SASA Highlights",
        "## Section 8: Integrated Interpretation",
        "## Section 9: Caveats and Limitations",
        "## Section 10: Artifacts and Reproduction",
    ],
)
def test_section_headings_present(report_text: str, heading: str):
    assert heading in report_text, f"Missing heading: {heading}"


def test_section_order(report_text: str):
    positions = []
    for n in range(2, 11):
        match = re.search(rf"## Section {n}:", report_text)
        assert match, f"Section {n} heading missing"
        positions.append(match.start())
    assert positions == sorted(positions)


def test_key_metrics_present(report_text: str):
    assert "8.24" in report_text  # overall RMSD
    assert "214" in report_text  # n aligned
    assert "P69441" in report_text  # UniProt accession
    assert "Escherichia coli" in report_text or "E. coli" in report_text


@pytest.mark.parametrize(
    "marker",
    [
        "(per RCSB)",
        "(per UniProt",
        "(general background)",
    ],
)
def test_provenance_markers_used(report_text: str, marker: str):
    assert marker in report_text, f"Provenance marker {marker!r} missing"


def test_run_derived_marker_used(report_text: str):
    """At least one of (run-derived) or (inferred from run) must appear."""
    assert "(run-derived)" in report_text or "(inferred from run)" in report_text


def test_no_fake_citations(report_text: str):
    """No author-year citation patterns allowed.

    Matches author-year constructs like:
        - 'Müller & Schulz 1992'
        - 'Smith et al. (2020)'
        - 'Jones and Brown, 1988'

    Requires a 4-digit year (19xx or 20xx) near the author tokens so
    that ordinary English prose like 'NMPbind and LID' or
    'Caveats and Limitations' does not match.
    """
    pattern = re.compile(
        r"[A-Z]\w+"
        r"(?:\s+(?:&|and)\s+[A-Z]\w+|\s+et\s*al\.?)"
        r"\s*,?\s*\(?(?:19|20)\d{2}\)?"
    )
    matches = pattern.findall(report_text)
    assert matches == [], f"Fake citation patterns found: {matches}"


def test_report_is_english(report_text: str):
    cjk = re.findall(r"[\u3000-\u9fff]", report_text)
    assert cjk == [], f"Report contains CJK characters: {cjk[:10]}"


def test_english_ratio_dominant(report_text: str):
    """ASCII-range characters should dominate (>= 90%)."""
    if not report_text:
        return
    ascii_count = sum(1 for ch in report_text if ord(ch) < 128)
    ratio = ascii_count / len(report_text)
    assert ratio >= 0.9, f"ASCII ratio too low: {ratio:.2f}"
