"""Validación estructural contra JSON Schema Draft 2020-12.

Bitácora:
    2026-08-30 - Validador inicial con comprobación explícita de formatos.

JSON Schema comprueba forma, tipos y restricciones locales. Las relaciones entre
IDs, páginas, cajas y recursos se delegan en :mod:`semantic`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from .issues import DatasetValidationError, ValidationIssue


def load_json(path: str | Path) -> Any:
    """Carga JSON UTF-8 y conserva los errores nativos con su posición."""

    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def build_validator(schema: Mapping[str, Any]) -> Draft202012Validator:
    """Comprueba primero el esquema y devuelve un validador reutilizable."""

    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_schema(
    instance: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> tuple[ValidationIssue, ...]:
    """Devuelve todos los errores estructurales en orden determinista."""

    validator = build_validator(schema)
    issues = []
    for error in sorted(validator.iter_errors(instance), key=_error_sort_key):
        path = "$" + "".join(f"[{item}]" if isinstance(item, int) else f".{item}" for item in error.path)
        issues.append(ValidationIssue("SCHEMA_INVALID", path, error.message))
    return tuple(issues)


def require_valid_schema(
    instance: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> None:
    """Lanza un error agregado cuando el dataset incumple el contrato."""

    issues = validate_schema(instance, schema)
    if issues:
        raise DatasetValidationError(issues)


def _error_sort_key(error: Any) -> tuple[str, str]:
    return ("/".join(str(item) for item in error.path), error.message)
