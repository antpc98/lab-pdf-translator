"""Barrera única de calidad para autorizar cambios del laboratorio.

Bitácora:
    2026-08-30 - Primera barrera integral: dependencias, pruebas, cobertura y aceptación.

La orquestación vive en el paquete para que el script, las pruebas y una futura CI
usen la misma definición de éxito. Ningún control se considera opcional.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .automation import ValidationReport, run_phase0_validation


@dataclass(frozen=True, slots=True)
class GateCheck:
    """Resultado estable de una etapa obligatoria de la barrera."""

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class QualityGateReport:
    """Resultado agregado; solo aprueba cuando todas las etapas pasan."""

    checks: tuple[GateCheck, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


CommandRunner = Callable[[Sequence[str], Path], int]
Phase0Runner = Callable[[Path], ValidationReport]


def run_quality_gate(
    project_root: str | Path,
    *,
    python_executable: str = sys.executable,
    command_runner: CommandRunner | None = None,
    phase0_runner: Phase0Runner = run_phase0_validation,
) -> QualityGateReport:
    """Ejecuta todas las evidencias exigidas para aprobar una entrega.

    Las pruebas incluyen explícitamente ``--cov`` para impedir que una ejecución
    aparentemente correcta omita por accidente el umbral definido en pyproject.
    Se ejecutan todas las etapas para entregar un diagnóstico completo.
    """

    root = Path(project_root).resolve()
    runner = command_runner or _run_command

    dependency_code = runner((python_executable, "-m", "pip", "check"), root)
    test_code = runner(
        (
            python_executable,
            "-m",
            "pytest",
            "--cov=lab_pdf_translator",
            "--cov-report=term-missing",
        ),
        root,
    )
    phase0 = phase0_runner(root)

    checks = (
        GateCheck(
            "dependencies",
            dependency_code == 0,
            "installed dependencies are coherent" if dependency_code == 0 else "pip check failed",
        ),
        GateCheck(
            "tests_and_coverage",
            test_code == 0,
            "pytest passed and coverage reached the configured threshold"
            if test_code == 0
            else "pytest or the coverage threshold failed",
        ),
        GateCheck(
            "phase0_acceptance",
            phase0.passed,
            _phase0_detail(phase0),
        ),
    )
    return QualityGateReport(checks)


def _run_command(command: Sequence[str], cwd: Path) -> int:
    """Ejecuta una etapa mostrando su salida y devuelve solo su código."""

    completed = subprocess.run(command, cwd=cwd, check=False)
    return completed.returncode


def _phase0_detail(report: ValidationReport) -> str:
    failed = [check.name for check in report.checks if not check.passed]
    if failed:
        return f"failed checks: {', '.join(failed)}"
    return f"{len(report.checks)} contract and PDF checks passed"
