"""Fixtures compartidas por las pruebas unitarias e integradas.

Bitácora: 2026-08-30 - Fixtures iniciales para contrato y repositorio.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from lab_pdf_translator.validation.schema import load_json


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Devuelve la raíz estable sin depender del directorio de ejecución."""

    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def document_schema(project_root: Path) -> dict[str, Any]:
    return load_json(project_root / "schemas" / "document.schema.json")


@pytest.fixture(scope="session")
def representative_document(project_root: Path) -> dict[str, Any]:
    return load_json(
        project_root / "schemas" / "examples" / "document.representative.valid.json"
    )


@pytest.fixture(scope="session")
def minimal_document(project_root: Path) -> dict[str, Any]:
    return load_json(project_root / "schemas" / "examples" / "document.minimal.valid.json")
