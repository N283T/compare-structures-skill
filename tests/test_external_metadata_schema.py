"""Tests for schemas/external_metadata.schema.json."""

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
    """The schema itself must be a valid Draft 2020-12 schema."""
    schema = _load_schema()
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize(
    "fixture_name",
    ["all_ok.json", "partial_failure.json", "all_failed.json"],
)
def test_fixture_validates(fixture_name: str):
    """Every bundled fixture must validate against the schema."""
    schema = _load_schema()
    instance = _load_fixture(fixture_name)
    Draft202012Validator(schema).validate(instance)


def test_missing_required_top_level_key_fails():
    """Dropping a required top-level key must fail validation."""
    schema = _load_schema()
    instance = _load_fixture("all_ok.json")
    del instance["structures"]
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)


def test_fetch_ok_must_be_bool():
    """fetch_ok fields must be booleans, not strings."""
    schema = _load_schema()
    instance = _load_fixture("all_ok.json")
    instance["structures"]["1AKE"]["fetch_ok"] = "yes"
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)


def test_source_must_start_with_togomcp_prefix():
    """Every source field must be prefixed with 'togomcp:'."""
    schema = _load_schema()
    instance = _load_fixture("all_ok.json")
    instance["structures"]["1AKE"]["source"] = "manual"
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(instance)
