"""Pruebas integradas de las muestras PDF reales y sintéticas.

Bitácora: 2026-08-30 - Regresión del libro inicial y fixture controlada.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from tests.fixtures.representative_pdf import build_representative_pdf


@pytest.mark.integration
def test_synthetic_pdf_covers_representative_layouts(tmp_path: Path) -> None:
    output = build_representative_pdf(tmp_path / "representative.pdf")
    with pymupdf.open(output) as document:
        assert document.page_count == 3
        assert "First governed item" in document[0].get_text("text")
        assert "sha256" in document[1].get_text("text")
        assert len(document[1].get_images(full=True)) == 1
        assert "Left column line 6" in document[2].get_text("text")
        assert "Right column line 6" in document[2].get_text("text")
        assert "Page 3 of 3" in document[2].get_text("text")


@pytest.mark.integration
def test_reference_pdf_is_present_and_has_expected_page_count(project_root: Path) -> None:
    pdf_files = sorted((project_root / "input").glob("*.pdf"))
    assert len(pdf_files) == 1
    with pymupdf.open(pdf_files[0]) as document:
        assert document.page_count == 284
