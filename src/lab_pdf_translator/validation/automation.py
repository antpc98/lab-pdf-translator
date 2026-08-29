"""Orquestación de las validaciones automáticas de la fase 0.

Bitácora:
    2026-08-30 - Suite inicial para configuración, contrato, ejemplos y PDF real.

El módulo devuelve datos estructurados y no imprime. La interfaz de terminal decide
cómo presentar el informe y qué código de salida utilizar.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import pymupdf
import yaml

from lab_pdf_translator.config import ConfigurationError, load_configuration

from .issues import ValidationIssue
from .schema import build_validator, load_json, validate_schema
from .semantic import validate_semantics


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Resultado de una comprobación independiente de la suite."""

    name: str
    passed: bool
    detail: str
    issues: tuple[ValidationIssue, ...] = ()


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Informe completo y apto para determinar el código de salida."""

    checks: tuple[CheckResult, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


def run_phase0_validation(project_root: str | Path) -> ValidationReport:
    """Ejecuta todas las barreras automáticas disponibles al cerrar la fase 0."""

    root = Path(project_root).resolve()
    checks = (
        _capture("configuration", lambda: _check_configuration(root)),
        _capture("schema_definition", lambda: _check_schema_definition(root)),
        _capture("contract_examples", lambda: _check_contract_examples(root)),
        _capture("pdf_samples", lambda: _check_pdf_samples(root)),
    )
    return ValidationReport(checks)


def _check_configuration(root: Path) -> str:
    configuration = load_configuration(root)
    return (
        f"settings and glossary valid; "
        f"source={configuration.settings['pipeline']['source_language']}; "
        f"target={configuration.settings['pipeline']['target_language']}"
    )


def _check_schema_definition(root: Path) -> str:
    schema = load_json(root / "schemas" / "document.schema.json")
    build_validator(schema)
    return "JSON Schema Draft 2020-12 definition is valid"


def _check_contract_examples(root: Path) -> str:
    schema = load_json(root / "schemas" / "document.schema.json")
    example_dir = root / "schemas" / "examples"
    valid_files = sorted(example_dir.glob("*.valid.json"))
    invalid_files = sorted(example_dir.glob("*.invalid.json"))
    if not valid_files or not invalid_files:
        raise ValueError("both valid and invalid contract examples are required")

    for path in valid_files:
        document = load_json(path)
        issues = (*validate_schema(document, schema), *validate_semantics(document))
        if issues:
            raise _IssuesFound(path.name, issues)

    validator = build_validator(schema)
    unexpectedly_valid = [
        path.name
        for path in invalid_files
        if not list(validator.iter_errors(load_json(path)))
    ]
    if unexpectedly_valid:
        raise ValueError(f"invalid examples accepted: {unexpectedly_valid}")
    return f"{len(valid_files)} valid examples accepted; {len(invalid_files)} invalid examples rejected"


def _check_pdf_samples(root: Path) -> str:
    manifest_path = root / "tests" / "fixtures" / "pdf-samples.yaml"
    with manifest_path.open("r", encoding="utf-8") as stream:
        manifest = yaml.safe_load(stream)
    if not isinstance(manifest, Mapping):
        raise ValueError("PDF sample manifest must be a YAML mapping")

    matches = sorted(root.glob(str(manifest["document_glob"])))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one reference PDF, found {len(matches)}")

    with pymupdf.open(matches[0]) as document:
        expected_pages = manifest["expected_page_count"]
        if document.page_count != expected_pages:
            raise ValueError(f"expected {expected_pages} pages, found {document.page_count}")
        for sample in manifest["samples"]:
            _validate_pdf_sample(document, sample)
    return f"{len(manifest['samples'])} representative pages verified in {expected_pages}-page PDF"


def _validate_pdf_sample(document: pymupdf.Document, sample: Mapping[str, Any]) -> None:
    number = sample["physical_page"]
    if not 1 <= number <= document.page_count:
        raise ValueError(f"sample page {number} is outside the document")
    page = document[number - 1]
    text = page.get_text("text")
    images = page.get_images(full=True)
    if len(text) < sample["minimum_text_characters"]:
        raise ValueError(
            f"page {number} ({sample['case']}) has {len(text)} text characters; "
            f"expected at least {sample['minimum_text_characters']}"
        )
    missing = [token for token in sample["required_text"] if token not in text]
    if missing:
        raise ValueError(f"page {number} ({sample['case']}) is missing text: {missing}")
    if len(images) < sample["minimum_images"]:
        raise ValueError(
            f"page {number} ({sample['case']}) has {len(images)} images; "
            f"expected at least {sample['minimum_images']}"
        )


def _capture(name: str, operation: Callable[[], str]) -> CheckResult:
    try:
        detail = operation()
    except _IssuesFound as exc:
        return CheckResult(name, False, str(exc), exc.issues)
    except (ConfigurationError, OSError, ValueError, yaml.YAMLError) as exc:
        issue = ValidationIssue("AUTOMATION_FAILED", "$", str(exc))
        return CheckResult(name, False, str(exc), (issue,))
    return CheckResult(name, True, detail)


class _IssuesFound(ValueError):
    def __init__(self, source: str, issues: tuple[ValidationIssue, ...]) -> None:
        self.issues = issues
        super().__init__(f"{source} produced {len(issues)} validation issue(s)")
