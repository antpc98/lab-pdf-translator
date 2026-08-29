"""Pruebas de la barrera integral y de su política de fallo cerrado.

Bitácora: 2026-08-30 - Cobertura inicial de comandos, agregación y códigos de etapa.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from lab_pdf_translator.validation.automation import CheckResult, ValidationReport
from lab_pdf_translator.validation.quality_gate import run_quality_gate


def test_quality_gate_runs_every_required_stage(project_root: Path) -> None:
    commands: list[tuple[str, ...]] = []

    def successful_command(command: Sequence[str], cwd: Path) -> int:
        assert cwd == project_root.resolve()
        commands.append(tuple(command))
        return 0

    phase_report = ValidationReport((CheckResult("contract", True, "valid"),))
    report = run_quality_gate(
        project_root,
        python_executable="python-under-test",
        command_runner=successful_command,
        phase0_runner=lambda root: phase_report,
    )

    assert report.passed
    assert commands[0] == ("python-under-test", "-m", "pip", "check")
    assert commands[1][:3] == ("python-under-test", "-m", "pytest")
    assert "--cov=lab_pdf_translator" in commands[1]
    assert "--cov-report=term-missing" in commands[1]


def test_quality_gate_fails_if_tests_or_coverage_fail(project_root: Path) -> None:
    calls = 0

    def failing_pytest(command: Sequence[str], cwd: Path) -> int:
        nonlocal calls
        calls += 1
        return 1 if "pytest" in command else 0

    phase_report = ValidationReport((CheckResult("contract", True, "valid"),))
    report = run_quality_gate(
        project_root,
        command_runner=failing_pytest,
        phase0_runner=lambda root: phase_report,
    )

    assert calls == 2
    assert not report.passed
    assert report.checks[1].name == "tests_and_coverage"
    assert not report.checks[1].passed


def test_quality_gate_reports_dependency_and_acceptance_failures(project_root: Path) -> None:
    phase_report = ValidationReport((CheckResult("pdf_samples", False, "missing"),))
    report = run_quality_gate(
        project_root,
        command_runner=lambda command, cwd: 1 if "pip" in command else 0,
        phase0_runner=lambda root: phase_report,
    )

    assert not report.passed
    assert not report.checks[0].passed
    assert report.checks[1].passed
    assert not report.checks[2].passed
    assert "pdf_samples" in report.checks[2].detail
