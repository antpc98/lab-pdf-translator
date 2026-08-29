"""Interfaz única para decidir si una entrega cumple la barrera de calidad.

Bitácora:
    2026-08-30 - Punto de entrada integral solicitado para el cierre de fase 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from lab_pdf_translator.validation.quality_gate import run_quality_gate  # noqa: E402


def main() -> int:
    """Ejecuta todas las etapas y devuelve 0 exclusivamente con aprobación total."""

    print("QUALITY GATE - PHASE 0", flush=True)
    print("=" * 72, flush=True)
    report = run_quality_gate(PROJECT_ROOT)
    print("=" * 72)
    for check in report.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"[{status}] {check.name}: {check.detail}")
    print("=" * 72)
    print("RESULT: PASS" if report.passed else "RESULT: FAIL")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
