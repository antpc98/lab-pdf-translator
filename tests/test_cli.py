"""Pruebas del contrato de salida de la CLI.

Bitácora:
    2026-09-05 - Fase 1: códigos de salida de extracción.
"""
from __future__ import annotations
from pathlib import Path
from lab_pdf_translator import __main__
from lab_pdf_translator.extraction.service import ExtractionError

def test_cli_success(monkeypatch, capsys) -> None:
    monkeypatch.setattr(__main__, "discover_pdf", lambda *_: Path("a.pdf"))
    monkeypatch.setattr(__main__, "extract_pdf", lambda *_args, **_kwargs: {"page_count": 1, "assets": []})
    assert __main__.main(["extract"]) == 0
    assert "PASS" in capsys.readouterr().out

def test_cli_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr(__main__, "discover_pdf", lambda *_: (_ for _ in ()).throw(ExtractionError("bad input")))
    assert __main__.main(["extract"]) == 2
    assert "ERROR" in capsys.readouterr().out
