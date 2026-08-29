"""Interfaz de terminal para las validaciones automáticas de la fase 0.

Bitácora:
    2026-08-30 - Comando inicial con salida humana y códigos aptos para CI.
"""

from __future__ import annotations

import sys
from pathlib import Path

# El script debe funcionar desde un checkout sin instalación editable. La lógica
# sigue residiendo en el paquete; esta inserción solo facilita el arranque inicial.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from lab_pdf_translator.validation.automation import run_phase0_validation  # noqa: E402


def main() -> int:
    """Imprime un informe estable y devuelve 0 únicamente si todo pasa."""

    report = run_phase0_validation(PROJECT_ROOT)
    print("PHASE 0 VALIDATION")
    print("=" * 72)
    for check in report.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"[{status}] {check.name}: {check.detail}")
        for issue in check.issues:
            print(f"       {issue.format()}")
    print("=" * 72)
    print("RESULT: PASS" if report.passed else "RESULT: FAIL")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
