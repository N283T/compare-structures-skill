"""Structural snapshot for examples/1ake_vs_4ake/report.md.

Does not lock prose content; only locks headings, key numeric
strings, provenance marker presence, and the absence of fake
citations or CJK characters.

The snapshot locks structure rather than prose because prose is
legitimately variable across regenerations (different wording,
different sentence order) while the skeleton and key facts must
stay stable. A structural snapshot catches the regressions that
matter (dropped section, dropped metric, broken provenance
discipline, accidental Japanese fallback) without false-positiving
on prose edits.
"""

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_REPORT_PATH = _REPO_ROOT.joinpath("examples", "1ake_vs_4ake", "report.md")

# CJK range broadened to include halfwidth Katakana and fullwidth
# Latin (U+FF00-U+FFEF) so accidentally-pasted fullwidth punctuation
# from a Japanese editor is caught too.
_CJK_PATTERN = re.compile(r"[\u3000-\u9fff\uff00-\uffef]")


@pytest.fixture(scope="module")
def report_text() -> str:
    return _REPORT_PATH.read_text(encoding="utf-8")


def test_report_exists(report_text: str):
    assert len(report_text) > 0


def test_h1_heading(report_text: str):
    """The H1 must name both structures and the comparison type."""
    assert report_text.startswith("# 1AKE vs 4AKE — Conformational Comparison")


def test_section_1_metadata_rows(report_text: str):
    """Section 1 body must include the generated-timestamp line and the Headline label.

    These two elements are load-bearing parts of the Section 1 block
    specified by the prompt's "Render as" example; they are equally
    important as the H1 itself and would be silently lost under a
    careless regeneration.
    """
    assert "*Generated " in report_text, "Section 1 missing '*Generated ...' line"
    assert "**Headline:**" in report_text, "Section 1 missing bold Headline label"


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
    """Each of Sections 2-10 must appear as a literal H2 heading."""
    assert heading in report_text, f"Missing heading: {heading}"


def test_section_order(report_text: str):
    """H2 Sections 2-10 must appear in strictly increasing order."""
    positions = []
    for n in range(2, 11):
        match = re.search(rf"## Section {n}:", report_text)
        assert match, f"Section {n} heading missing"
        positions.append(match.start())
    assert positions == sorted(positions)


def test_key_metrics_present(report_text: str):
    """The report must cite the key 1AKE/4AKE numerical and identity facts.

    These specific strings are drawn from facts.json and
    external_metadata.json for this example. Absence signals that
    the regeneration either pulled from the wrong source or failed
    to surface core metrics in the report body.
    """
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
    """Each major provenance marker family must appear in the report."""
    assert marker in report_text, f"Provenance marker {marker!r} missing"


def test_run_derived_marker_used(report_text: str):
    """At least one of (run-derived) or (inferred from run) must appear.

    The two markers are interchangeable for the purpose of this check
    because the example report may use either depending on whether a
    statement is a bare fact or a derived interpretation.
    """
    assert "(run-derived)" in report_text or "(inferred from run)" in report_text


def test_no_fake_citations(report_text: str):
    """No author-year citation patterns allowed.

    Matches author-year constructs like:
        - 'Müller & Schulz 1992'
        - 'Smith et al. (2020)'
        - 'Jones and Brown, 1988'

    Requires a 4-digit year (19xx or 20xx) near the author tokens so
    that ordinary English prose like 'NMPbind and LID' or
    'Caveats and Limitations' does not match. This tightening was
    added after an earlier version of the regex false-positived on
    those two phrases.
    """
    pattern = re.compile(
        r"[A-Z]\w+"
        r"(?:\s+(?:&|and)\s+[A-Z]\w+|\s+et\s*al\.?)"
        r"\s*,?\s*\(?(?:19|20)\d{2}\)?"
    )
    matches = pattern.findall(report_text)
    assert matches == [], f"Fake citation patterns found: {matches}"


def test_report_is_english(report_text: str):
    """No CJK or fullwidth characters allowed anywhere in the report.

    The report is English-only by design. Any CJK/fullwidth character
    typically indicates an accidental revert to an older Japanese
    version or a pasted Japanese quotation.
    """
    cjk = _CJK_PATTERN.findall(report_text)
    assert cjk == [], f"Report contains CJK/fullwidth characters: {cjk[:10]}"


def test_english_ratio_dominant(report_text: str):
    """ASCII-range characters should dominate the report body (>= 95%).

    The English report legitimately contains a small amount of
    non-ASCII (Cα, β, ΔSASA, Å, em-dashes, etc.). A ratio below 95%
    indicates the report has drifted toward non-English content and
    merits investigation; 95% leaves ample headroom for Greek and
    symbolic characters while still catching a whole-paragraph drift.
    """
    if not report_text:
        return
    ascii_count = sum(1 for ch in report_text if ord(ch) < 128)
    ratio = ascii_count / len(report_text)
    assert ratio >= 0.95, f"ASCII ratio too low: {ratio:.2%}"
