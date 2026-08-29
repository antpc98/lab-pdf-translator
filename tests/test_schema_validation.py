"""Pruebas automáticas del JSON Schema y sus ejemplos.

Bitácora: 2026-08-30 - Validación Draft 2020-12 y formatos explícitos.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lab_pdf_translator.validation.issues import DatasetValidationError
from lab_pdf_translator.validation.schema import (
    build_validator,
    load_json,
    require_valid_schema,
    validate_schema,
)


def test_document_schema_is_valid_draft_2020_12(document_schema: dict) -> None:
    validator = build_validator(document_schema)
    assert validator.META_SCHEMA["$id"].endswith("2020-12/schema")


def test_all_valid_examples_are_accepted(project_root: Path, document_schema: dict) -> None:
    paths = sorted((project_root / "schemas" / "examples").glob("*.valid.json"))
    assert paths, "At least one valid example is required"
    for path in paths:
        assert validate_schema(load_json(path), document_schema) == ()


def test_all_invalid_examples_are_rejected(project_root: Path, document_schema: dict) -> None:
    paths = sorted((project_root / "schemas" / "examples").glob("*.invalid.json"))
    assert paths, "At least one invalid example is required"
    for path in paths:
        assert validate_schema(load_json(path), document_schema), path.name


def test_require_valid_schema_aggregates_errors(
    project_root: Path, document_schema: dict
) -> None:
    invalid = load_json(
        project_root / "schemas" / "examples" / "document.bad-identity.invalid.json"
    )
    with pytest.raises(DatasetValidationError) as exc_info:
        require_valid_schema(invalid, document_schema)
    assert len(exc_info.value.issues) >= 5
    assert "SCHEMA_INVALID" in str(exc_info.value)
