"""Tests for schemas/external_metadata.schema.json.

The schema is the contract between the togomcp fetch step in the
SKILL.md workflow and the report-authoring prompt. This test module
guards the contract by validating bundled fixtures against the schema
(positive cases) and by mutating known-good fixtures to exercise each
load-bearing constraint (negative cases).

The fixtures under tests/fixtures/external_metadata/ mirror the three
graceful-degradation rows documented in the design spec Section 4.4
(all-ok, partial failure, full togomcp-down), so the happy-path tests
double as smoke tests that realistic degradation modes are accepted.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCHEMA_PATH = _REPO_ROOT.joinpath("schemas", "external_metadata.schema.json")
_FIXTURE_DIR = Path(__file__).parent.joinpath("fixtures", "external_metadata")


def _load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text())


def _load_fixture(name: str) -> dict:
    return json.loads(_FIXTURE_DIR.joinpath(name).read_text())


def test_schema_is_valid_draft_2020_12():
    """The schema itself must be a valid Draft 2020-12 schema.

    Catches malformed schemas that silently validate everything by
    falling back to permissive defaults.
    """
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize(
    "fixture_name",
    ["all_ok.json", "partial_failure.json", "all_failed.json"],
)
def test_fixture_validates(fixture_name: str):
    """Every bundled fixture must validate against the schema.

    The three fixtures match the graceful-degradation table in the
    design spec Section 4.4. Any one of them failing to validate would
    indicate a contract drift between the schema and the documented
    degradation rows.
    """
    schema = _load_schema()
    instance = _load_fixture(fixture_name)
    Draft202012Validator(schema).validate(instance)


def test_missing_required_top_level_key_fails():
    """Dropping a required top-level key must fail validation.

    Guards against a schema edit that weakens top-level required
    fields, which would let a writer silently emit an incomplete
    artifact.
    """
    schema = _load_schema()
    instance = _load_fixture("all_ok.json")
    del instance["structures"]
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)


def test_fetch_ok_must_be_bool():
    """fetch_ok fields must be booleans, not strings.

    Catches stringly-typed truthiness mistakes by an LLM writer that
    treats "yes" / "ok" as equivalent to true.
    """
    schema = _load_schema()
    instance = _load_fixture("all_ok.json")
    instance["structures"]["1AKE"]["fetch_ok"] = "yes"
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)


def test_source_must_start_with_togomcp_prefix():
    """Every source field must be prefixed with 'togomcp:'.

    The report prompt's provenance markers assume every fact in this
    artifact originated from a togomcp call. Allowing non-togomcp
    sources would break the "(per RCSB)" / "(per UniProt ...)" marker
    semantics by letting unverifiable claims into reports.
    """
    schema = _load_schema()
    instance = _load_fixture("all_ok.json")
    instance["structures"]["1AKE"]["source"] = "manual"
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)


@pytest.mark.parametrize(
    "path,key",
    [
        (("structures", "1AKE"), "error"),
        (("uniprot_entries", "P69441"), "organism"),
        (("uniprot_sparql", "P69441"), "domains"),
        (("uniprot_mapping",), "pairs"),
    ],
)
def test_nested_required_key_enforced(path: tuple[str, ...], key: str):
    """Required keys inside nested objects must also be enforced.

    The top-level required list is covered by
    test_missing_required_top_level_key_fails; this guards the
    equally-load-bearing nested required lists. Without this test,
    a schema edit that silently drops `required` from an inner object
    would let writers omit any field below the top level.
    """
    schema = _load_schema()
    instance = _load_fixture("all_ok.json")
    target = instance
    for p in path:
        target = target[p]
    del target[key]
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)


def test_additional_properties_rejected_at_top_level():
    """An unknown top-level key must fail validation.

    The schema sets `additionalProperties: false` at every level. This
    test pins the behavior at the top so a future edit that flips it
    to permissive is caught immediately.
    """
    schema = _load_schema()
    instance = _load_fixture("all_ok.json")
    instance["unexpected_key"] = 1
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)


def test_additional_properties_rejected_in_structures_entry():
    """An unknown key inside a structures entry must fail validation.

    Complements the top-level check by pinning inner-object strictness.
    """
    schema = _load_schema()
    instance = _load_fixture("all_ok.json")
    instance["structures"]["1AKE"]["unexpected"] = True
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)


def test_pairs_tuple_must_be_exactly_two_elements():
    """uniprot_mapping.pairs entries must be exactly 2-element tuples.

    The report prompt's Section 4a UniProt extraction depends on the
    [pdb_id, uniprot_acc] shape; a 1- or 3-element entry would
    silently corrupt that lookup.
    """
    schema = _load_schema()
    instance = _load_fixture("all_ok.json")
    instance["uniprot_mapping"]["pairs"].append(["only_one"])
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)


def test_domains_entry_requires_name_and_range():
    """uniprot_sparql.*.domains entries must have both name and range.

    Section 4c's moved-region-to-subdomain overlap check depends on
    parsing the `range` string as `start-end` integers. An entry
    missing `range` would silently disable the cross-check.
    """
    schema = _load_schema()
    instance = _load_fixture("all_ok.json")
    del instance["uniprot_sparql"]["P69441"]["domains"][0]["range"]
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)
