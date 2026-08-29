"""Pruebas de aceptación del comando automático de cierre de fase 0.

Bitácora: 2026-08-30 - Informe agregado y contrato de salida de terminal.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from lab_pdf_translator.validation.automation import run_phase0_validation


@pytest.mark.integration
def test_phase0_automation_passes_all_checks(project_root: Path) -> None:
    report = run_phase0_validation(project_root)
    assert report.passed
    assert [check.name for check in report.checks] == [
        "configuration",
        "schema_definition",
        "contract_examples",
        "pdf_samples",
    ]
    assert all(check.passed for check in report.checks)


@pytest.mark.integration
def test_phase0_cli_returns_zero_and_expected_summary(project_root: Path) -> None:
    completed = subprocess.run(
        [sys.executable, str(project_root / "scripts" / "validate_phase0.py")],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "[PASS] configuration" in completed.stdout
    assert "[PASS] contract_examples" in completed.stdout
    assert "[PASS] pdf_samples" in completed.stdout
    assert "RESULT: PASS" in completed.stdout


def test_automation_aggregates_failures_in_incomplete_checkout(tmp_path: Path) -> None:
    report = run_phase0_validation(tmp_path)
    assert not report.passed
    assert len(report.checks) == 4
    assert all(not check.passed for check in report.checks)
    assert all(check.issues[0].code == "AUTOMATION_FAILED" for check in report.checks)
