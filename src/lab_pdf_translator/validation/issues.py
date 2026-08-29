"""Tipos comunes para comunicar fallos de validación.

Bitácora:
    2026-08-30 - Modelo inicial de incidencias e informe agregado.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """Incidencia estable y serializable para CLI, logs y pruebas."""

    code: str
    path: str
    message: str

    def format(self) -> str:
        """Devuelve una línea legible sin perder el código procesable."""

        return f"[{self.code}] {self.path}: {self.message}"


class DatasetValidationError(ValueError):
    """Error agregado que evita ocultar fallos posteriores al primero."""

    def __init__(self, issues: Iterable[ValidationIssue]) -> None:
        self.issues = tuple(issues)
        detail = "\n".join(issue.format() for issue in self.issues)
        super().__init__(detail or "Dataset validation failed without details")
