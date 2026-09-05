"""Extracción RAW determinista de PDFs digitales.

Bitácora:
    2026-09-05 - Fase 1: extracción, checkpoints y publicación atómica inicial.
"""

from __future__ import annotations

import json
import logging
import mimetypes
import os
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pymupdf

from lab_pdf_translator.models.identifiers import (
    asset_id, asset_occurrence_id, block_id, document_id, line_id, page_id,
    sha256_bytes, sha256_file, span_id,
)
from lab_pdf_translator.validation.schema import load_json, validate_schema
from lab_pdf_translator.validation.semantic import validate_semantics


class ExtractionError(RuntimeError):
    """Error operativo que no debe publicar un RAW incompleto."""


def discover_pdf(input_dir: str | Path, explicit: str | Path | None = None) -> Path:
    """Resuelve un PDF explícito o el único PDF regular en ``input_dir``."""
    if explicit is not None:
        path = Path(explicit).resolve()
        if not path.is_file() or path.suffix.lower() != ".pdf":
            raise ExtractionError(f"Input PDF is not a readable .pdf file: {path}")
        return path
    matches = sorted(path for path in Path(input_dir).glob("*.pdf") if path.is_file())
    if not matches:
        raise ExtractionError(f"No PDF found in {Path(input_dir)}")
    if len(matches) > 1:
        names = ", ".join(path.name for path in matches)
        raise ExtractionError(f"Multiple PDFs found; pass --input explicitly: {names}")
    return matches[0].resolve()


def extract_pdf(
    project_root: str | Path,
    pdf_path: str | Path,
    *,
    resume: bool = False,
    fail_after_page: int | None = None,
) -> dict[str, Any]:
    """Extrae y valida un PDF, y publica el resultado sólo al final.

    ``fail_after_page`` es una sonda de prueba deliberada para demostrar resume;
    nunca forma parte de la CLI pública.
    """
    root = Path(project_root).resolve()
    source = Path(pdf_path).resolve()
    if not source.is_file():
        raise ExtractionError(f"Input file not found: {source}")
    source_sha = sha256_file(source)
    doc_id = document_id(source_sha)
    checkpoint_dir = root / "checkpoints" / doc_id
    checkpoint_file = checkpoint_dir / "checkpoint.json"
    stage_images = checkpoint_dir / "images"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    stage_images.mkdir(exist_ok=True)
    state = _load_checkpoint(checkpoint_file, source_sha) if resume else None
    if state is None:
        state = {"source_sha256": source_sha, "pages": {}, "assets": {}}
    logger = _logger(root)
    logger.info("Extracting %s sha256=%s", source.name, source_sha)
    try:
        with pymupdf.open(source) as pdf:
            if pdf.needs_pass:
                raise ExtractionError("Encrypted PDF is not supported without a password")
            if not 1 <= pdf.page_count <= 1000:
                raise ExtractionError(f"PDF page count must be 1..1000; got {pdf.page_count}")
            for number in range(1, pdf.page_count + 1):
                key = str(number)
                if key not in state["pages"]:
                    page, assets = _extract_page(pdf[number - 1], number, doc_id, stage_images)
                    state["pages"][key] = page
                    state["assets"].update(assets)
                    _save_checkpoint(checkpoint_file, state)
                    logger.info("page=%s blocks=%s assets=%s", number, len(page["blocks"]), len(assets))
                if fail_after_page == number:
                    raise ExtractionError(f"Simulated interruption after page {number}")
            document = _build_document(source, source_sha, doc_id, pdf.page_count, state)
    except pymupdf.FileDataError as exc:
        raise ExtractionError(f"Unreadable PDF: {source.name}: {exc}") from exc
    schema = load_json(root / "schemas" / "document.schema.json")
    issues = (*validate_schema(document, schema), *validate_semantics(document))
    if issues:
        raise ExtractionError("RAW validation failed: " + "; ".join(str(issue) for issue in issues[:5]))
    _publish(root, document, stage_images, state["assets"])
    shutil.rmtree(checkpoint_dir, ignore_errors=True)
    logger.info("Extraction complete pages=%s", document["page_count"])
    return document


def _extract_page(page: pymupdf.Page, number: int, doc_id: str, image_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    precision = 4
    pid = page_id(doc_id, number)
    rect = page.rect
    width, height = _number(rect.width), _number(rect.height)
    image_specs: list[dict[str, Any]] = []
    assets: dict[str, Any] = {}
    for index, image in enumerate(page.get_images(full=True)):
        xref = image[0]
        try:
            payload = page.parent.extract_image(xref)
        except (ValueError, RuntimeError):
            continue
        content = payload.get("image", b"")
        if not content:
            continue
        digest = sha256_bytes(content)
        aid = asset_id(digest)
        extension = str(payload.get("ext") or "bin").lower()
        filename = f"{digest}.{extension}"
        destination = image_dir / filename
        if not destination.exists():
            destination.write_bytes(content)
        assets[aid] = {
            "asset_id": aid, "sha256": digest,
            "media_type": mimetypes.types_map.get(f".{extension}", "application/octet-stream"),
            "byte_size": len(content), "path": f"assets/images/{filename}",
            "pixel_width": payload.get("width"), "pixel_height": payload.get("height"),
        }
        for occurrence_index, image_rect in enumerate(page.get_image_rects(xref), start=1):
            image_specs.append({"asset_id": aid, "bbox": _bbox(image_rect, width, height), "source_index": index * 10000 + occurrence_index})
    image_specs.sort(key=lambda value: (*value["bbox"], value["asset_id"], value["source_index"]))
    occurrences = []
    for order, item in enumerate(image_specs, start=1):
        occurrences.append({"asset_occurrence_id": asset_occurrence_id(pid, item["asset_id"], order), "asset_id": item["asset_id"], "occurrence_order": order, "source_index": item["source_index"], "bbox": item["bbox"], "transform": [1, 0, 0, 1, 0, 0]})
    raw_blocks = page.get_text("dict", flags=pymupdf.TEXTFLAGS_DICT).get("blocks", [])
    records = []
    for source_index, raw in enumerate(raw_blocks):
        if raw.get("type") != 0:
            continue
        lines = raw.get("lines", [])
        if not lines:
            continue
        records.append({"source_index": source_index, "bbox": _bbox(raw["bbox"], width, height), "lines": lines})
    records.sort(key=lambda value: (*value["bbox"], value["source_index"]))
    blocks = [_block(record, order, pid, width, height) for order, record in enumerate(records, start=1)]
    # A visual image block lets each occurrence retain the contract's block relation.
    for occurrence in occurrences:
        blocks.append({"source_index": occurrence["source_index"], "bbox": occurrence["bbox"], "lines": [], "_occurrence": occurrence["asset_occurrence_id"]})
    blocks.sort(key=lambda value: (*value["bbox"], value["source_index"]))
    final_blocks = []
    for order, raw_block in enumerate(blocks, start=1):
        if "block_id" in raw_block:
            raw_block["block_id"] = block_id(pid, order)
            # IDs below depend on final block identity; rebuild textual children.
            raw_block = _block({"source_index": raw_block["source_index"], "bbox": raw_block["bbox"], "lines": raw_block.pop("_raw_lines")}, order, pid, width, height)
            raw_block.pop("_raw_lines")
        else:
            raw_block = {"block_id": block_id(pid, order), "block_order": order, "source_index": raw_block["source_index"], "block_type": "image", "bbox": raw_block["bbox"], "lines": [], "asset_occurrence_ids": [raw_block["_occurrence"]]} 
        final_blocks.append(raw_block)
    return ({"page_id": pid, "page_number": number, "printed_page_label": None, "width": width, "height": height, "rotation": page.rotation, "media_box": _bbox(page.mediabox, width, height), "status": "complete", "blocks": final_blocks, "asset_occurrences": occurrences, "warnings": []}, assets)


def _block(record: dict[str, Any], order: int, pid: str, width: float, height: float) -> dict[str, Any]:
    bid = block_id(pid, order)
    lines_data = []
    for source_index, line in enumerate(record["lines"]):
        lines_data.append({"source_index": source_index, "bbox": _bbox(line["bbox"], width, height), "spans": line.get("spans", [])})
    lines_data.sort(key=lambda value: (*value["bbox"], value["source_index"]))
    lines = []
    for line_order, line in enumerate(lines_data, start=1):
        lid = line_id(bid, line_order)
        spans_data = [{"source_index": index, "raw": span, "bbox": _bbox(span["bbox"], width, height)} for index, span in enumerate(line["spans"])]
        spans_data.sort(key=lambda value: (*value["bbox"], value["source_index"]))
        spans = [_span(item, span_order, lid) for span_order, item in enumerate(spans_data, start=1)]
        lines.append({"line_id": lid, "line_order": line_order, "source_index": line["source_index"], "bbox": line["bbox"], "spans": spans})
    text = "".join(span["text"] for line in lines for span in line["spans"])
    return {"block_id": bid, "block_order": order, "source_index": record["source_index"], "block_type": _classify(text, lines), "bbox": record["bbox"], "lines": lines, "asset_occurrence_ids": [], "_raw_lines": record["lines"]}


def _span(item: dict[str, Any], order: int, lid: str) -> dict[str, Any]:
    raw = item["raw"]
    flags = int(raw.get("flags", 0))
    color = raw.get("color")
    return {"span_id": span_id(lid, order), "span_order": order, "source_index": item["source_index"], "text": raw.get("text", ""), "bbox": item["bbox"], "font": {"family": raw.get("font"), "size": _number(raw["size"]) if raw.get("size") else None, "weight": "bold" if flags & 16 else "normal", "style": "italic" if flags & 2 else "normal", "color": f"#{color:06X}" if isinstance(color, int) else None}, "rotation": 0, "is_visible": True}


def _classify(text: str, lines: list[dict[str, Any]]) -> str:
    if not text:
        return "unknown"
    stripped = text.strip()
    if stripped.isdigit() and len(stripped) <= 4:
        return "page_number"
    if stripped.startswith(("•", "- ", "– ", "* ")):
        return "list_item"
    if len(lines) == 1 and len(stripped) < 100 and lines[0]["spans"] and lines[0]["spans"][0]["font"]["weight"] == "bold":
        return "heading"
    return "paragraph"


def _bbox(value: Any, width: float, height: float) -> list[float]:
    x0, y0, x1, y1 = value
    return [_number(max(0, min(width, x0))), _number(max(0, min(height, y0))), _number(max(0, min(width, x1))), _number(max(0, min(height, y1)))]


def _number(value: float) -> float:
    return round(float(value), 4)


def _build_document(source: Path, digest: str, doc_id: str, pages: int, state: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": "1.0.0", "id_scheme_version": 1, "document_id": doc_id, "source": {"file_name": source.name, "mime_type": "application/pdf", "byte_size": source.stat().st_size, "sha256": digest}, "extraction": {"extractor_name": "PyMuPDF", "extractor_version": pymupdf.VersionBind, "extracted_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"), "status": "complete"}, "page_count": pages, "pages": [state["pages"][str(index)] for index in range(1, pages + 1)], "assets": sorted(state["assets"].values(), key=lambda value: value["asset_id"]), "warnings": []}


def _load_checkpoint(path: Path, digest: str) -> dict[str, Any] | None:
    if not path.exists(): return None
    try: state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc: raise ExtractionError(f"Corrupt checkpoint: {path}") from exc
    if state.get("source_sha256") != digest: raise ExtractionError("Checkpoint belongs to a different input PDF")
    return state


def _save_checkpoint(path: Path, state: dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    for attempt in range(5):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.1 * (attempt + 1))


def _publish(root: Path, document: dict[str, Any], stage_images: Path, assets: dict[str, Any]) -> None:
    destination_images = root / "assets" / "images"; destination_images.mkdir(parents=True, exist_ok=True)
    for asset in assets.values():
        filename = Path(asset["path"]).name
        staged = stage_images / filename
        if staged.exists(): os.replace(staged, destination_images / filename)
    output = root / "data" / "raw" / "document.json"; output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, output)


def _logger(root: Path) -> logging.Logger:
    logger = logging.getLogger("lab_pdf_translator.extraction")
    if not logger.handlers:
        (root / "logs").mkdir(exist_ok=True)
        handler = logging.FileHandler(root / "logs" / "phase-1-extraction.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler); logger.setLevel(logging.INFO)
    return logger
