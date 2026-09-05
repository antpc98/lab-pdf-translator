"""Pruebas de Fase 1 con un PDF sintético reproducible.

Bitácora:
    2026-09-05 - Fase 1: cobertura de extracción, publicación y reanudación.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pymupdf
import pytest

from lab_pdf_translator.extraction import service
from lab_pdf_translator.extraction.service import ExtractionError, discover_pdf, extract_pdf
from lab_pdf_translator.validation.schema import load_json, validate_schema
from lab_pdf_translator.validation.semantic import validate_semantics


def _root(tmp_path: Path, project_root: Path) -> Path:
    shutil.copytree(project_root / "schemas", tmp_path / "schemas")
    (tmp_path / "input").mkdir(); (tmp_path / "assets" / "images").mkdir(parents=True)
    (tmp_path / "data" / "raw").mkdir(parents=True)
    return tmp_path


def _pdf(path: Path) -> None:
    document = pymupdf.open()
    first = document.new_page(); first.insert_text((72, 72), "Hello     world", fontsize=12, fontname="hebo")
    first.insert_text((72, 100), "• raw list", fontsize=10)
    second = document.new_page()  # Empty text pages must survive.
    pixel = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.Rect(0, 0, 2, 2), False)
    pixel.clear_with(0xFF0000)
    second.insert_image(pymupdf.Rect(20, 20, 40, 40), stream=pixel.tobytes("png"))
    document.new_page()
    document.save(path); document.close()


def test_discovery_requires_one_pdf(tmp_path: Path) -> None:
    with pytest.raises(ExtractionError, match="No PDF"):
        discover_pdf(tmp_path)
    _pdf(tmp_path / "a.pdf"); _pdf(tmp_path / "b.pdf")
    with pytest.raises(ExtractionError, match="Multiple PDFs"):
        discover_pdf(tmp_path)
    assert discover_pdf(tmp_path, tmp_path / "a.pdf").name == "a.pdf"
    with pytest.raises(ExtractionError, match="readable"):
        discover_pdf(tmp_path, tmp_path / "missing.pdf")


def test_extract_validate_and_resume(tmp_path: Path, project_root: Path) -> None:
    root = _root(tmp_path, project_root); source = root / "input" / "any-name.pdf"; _pdf(source)
    with pytest.raises(ExtractionError, match="Simulated"):
        extract_pdf(root, source, resume=True, fail_after_page=1)
    document = extract_pdf(root, source, resume=True)
    assert document["page_count"] == 3
    assert document["pages"][2]["blocks"] == []
    assert document["assets"] and document["pages"][1]["asset_occurrences"]
    assert document["pages"][0]["blocks"][0]["lines"][0]["spans"][0]["text"] == "Hello     world"
    schema = load_json(root / "schemas" / "document.schema.json")
    assert not validate_schema(document, schema)
    assert not validate_semantics(document)
    published = json.loads((root / "data" / "raw" / "document.json").read_text(encoding="utf-8"))
    assert published["pages"] == document["pages"]
    again = extract_pdf(root, source)
    assert again["document_id"] == document["document_id"]
    assert again["pages"] == document["pages"]


def test_checkpoint_wrong_or_corrupt_is_rejected(tmp_path: Path, project_root: Path) -> None:
    root = _root(tmp_path, project_root); source = root / "input" / "a.pdf"; _pdf(source)
    with pytest.raises(ExtractionError):
        extract_pdf(root, source, resume=True, fail_after_page=1)
    checkpoint = next((root / "checkpoints").glob("*/checkpoint.json"))
    checkpoint.write_text("{", encoding="utf-8")
    with pytest.raises(ExtractionError, match="Corrupt"):
        extract_pdf(root, source, resume=True)


def test_small_helpers_and_checkpoint_identity(tmp_path: Path) -> None:
    assert service._classify("", []) == "unknown"
    assert service._classify("12", []) == "page_number"
    assert service._classify("- item", []) == "list_item"
    assert service._classify("Title", [{"spans": [{"font": {"weight": "bold"}}]}]) == "heading"
    assert service._classify("plain", []) == "paragraph"
    assert service._bbox((-3, -2, 999, 999), 10, 20) == [0.0, 0.0, 10.0, 20.0]
    checkpoint = tmp_path / "checkpoint.json"
    checkpoint.write_text(json.dumps({"source_sha256": "other", "pages": {}, "assets": {}}), encoding="utf-8")
    with pytest.raises(ExtractionError, match="different"):
        service._load_checkpoint(checkpoint, "expected")
    service._save_checkpoint(checkpoint, {"source_sha256": "ok", "pages": {}, "assets": {}})
    assert service._load_checkpoint(checkpoint, "ok")["pages"] == {}
