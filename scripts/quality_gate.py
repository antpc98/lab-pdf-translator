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

from lab_pdf_translator.models.identifiers import sha256_file  # noqa: E402
from lab_pdf_translator.validation.quality_gate import run_quality_gate  # noqa: E402
from lab_pdf_translator.validation.schema import load_json, validate_schema  # noqa: E402
from lab_pdf_translator.validation.semantic import validate_semantics  # noqa: E402


def _phase1_raw_check() -> tuple[bool, str]:
    """Comprueba el RAW publicado y los recursos que declara, sin mutarlo."""
    path = PROJECT_ROOT / "data" / "raw" / "document.json"
    if not path.is_file():
        return False, "data/raw/document.json is missing; run Phase 1 extraction first"
    document = load_json(path)
    issues = (*validate_schema(document, load_json(PROJECT_ROOT / "schemas" / "document.schema.json")), *validate_semantics(document))
    missing = [asset["path"] for asset in document["assets"] if not (PROJECT_ROOT / asset["path"]).is_file()]
    mismatched = [asset["path"] for asset in document["assets"] if (PROJECT_ROOT / asset["path"]).is_file() and sha256_file(PROJECT_ROOT / asset["path"]) != asset["sha256"]]
    if issues or missing or mismatched:
        return False, f"schema/semantic/assets failed: issues={len(issues)} missing={len(missing)} hash_mismatches={len(mismatched)}"
    return True, f"RAW valid: pages={document['page_count']} assets={len(document['assets'])}"


def main() -> int:
    """Ejecuta todas las etapas y devuelve 0 exclusivamente con aprobación total."""

    print("QUALITY GATE - PHASE 1", flush=True)
    print("=" * 72, flush=True)
    report = run_quality_gate(PROJECT_ROOT)
    phase1_passed, phase1_detail = _phase1_raw_check()
    print("=" * 72)
    for check in report.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"[{status}] {check.name}: {check.detail}")
    print(f"[{'PASS' if phase1_passed else 'FAIL'}] phase1_raw: {phase1_detail}")
    print("=" * 72)
    passed = report.passed and phase1_passed
    print("RESULT: PASS" if passed else "RESULT: FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
