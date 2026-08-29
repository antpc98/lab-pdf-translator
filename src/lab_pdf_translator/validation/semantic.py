"""Validaciones semánticas que complementan el JSON Schema.

Bitácora:
    2026-08-30 - Controles iniciales de identidad, orden, geometría y recursos.

El validador no muta el dataset. Se espera que la validación estructural se haya
ejecutado antes; aun así, cada regla informa una ruta precisa para facilitar soporte.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence

from lab_pdf_translator.models.identifiers import (
    asset_id,
    asset_occurrence_id,
    block_id,
    document_id,
    line_id,
    page_id,
    span_id,
)

from .issues import DatasetValidationError, ValidationIssue


def validate_semantics(document: Mapping[str, Any]) -> tuple[ValidationIssue, ...]:
    """Ejecuta reglas relacionales y devuelve todas las incidencias encontradas."""

    issues: list[ValidationIssue] = []
    _validate_document_identity(document, issues)
    assets = _validate_assets(document.get("assets", []), issues)
    pages = document.get("pages", [])

    if document.get("page_count") != len(pages):
        _add(issues, "PAGE_COUNT_MISMATCH", "$.page_count", "must equal len(pages)")

    _validate_orders(
        [page.get("page_number") for page in pages],
        "$.pages",
        "PAGE_NUMBER_SEQUENCE",
        issues,
    )

    seen_ids: set[str] = set()
    for page_index, page in enumerate(pages):
        _validate_page(page, page_index, document.get("document_id"), assets, seen_ids, issues)

    return tuple(issues)


def require_valid_semantics(document: Mapping[str, Any]) -> None:
    """Interrumpe el pipeline si existe cualquier incoherencia semántica."""

    issues = validate_semantics(document)
    if issues:
        raise DatasetValidationError(issues)


def _validate_document_identity(
    document: Mapping[str, Any], issues: list[ValidationIssue]
) -> None:
    source_sha = document.get("source", {}).get("sha256")
    actual_id = document.get("document_id")
    try:
        expected_id = document_id(source_sha)
    except (TypeError, ValueError):
        return  # JSON Schema comunicará el formato inválido del hash.
    if actual_id != expected_id:
        _add(
            issues,
            "DOCUMENT_ID_MISMATCH",
            "$.document_id",
            f"expected {expected_id}",
        )


def _validate_assets(
    asset_items: Sequence[Mapping[str, Any]],
    issues: list[ValidationIssue],
) -> dict[str, Mapping[str, Any]]:
    assets: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(asset_items):
        path = f"$.assets[{index}]"
        actual_id = item.get("asset_id")
        try:
            expected_id = asset_id(item.get("sha256"))
        except (TypeError, ValueError):
            expected_id = None
        if expected_id is not None and actual_id != expected_id:
            _add(issues, "ASSET_ID_MISMATCH", f"{path}.asset_id", f"expected {expected_id}")
        if actual_id in assets:
            _add(issues, "DUPLICATE_ASSET_ID", f"{path}.asset_id", "must be unique")
        else:
            assets[actual_id] = item
        _validate_relative_asset_path(item.get("path"), f"{path}.path", issues)
    return assets


def _validate_page(
    page: Mapping[str, Any],
    page_index: int,
    parent_document_id: str,
    assets: Mapping[str, Mapping[str, Any]],
    seen_ids: set[str],
    issues: list[ValidationIssue],
) -> None:
    path = f"$.pages[{page_index}]"
    page_number = page.get("page_number")
    actual_page_id = page.get("page_id")
    try:
        expected_page_id = page_id(parent_document_id, page_number)
    except (TypeError, ValueError):
        expected_page_id = None
    if expected_page_id is not None and actual_page_id != expected_page_id:
        _add(issues, "PAGE_ID_MISMATCH", f"{path}.page_id", f"expected {expected_page_id}")
    _register_id(actual_page_id, f"{path}.page_id", seen_ids, issues)

    width, height = page.get("width"), page.get("height")
    occurrences = page.get("asset_occurrences", [])
    _validate_orders(
        [item.get("occurrence_order") for item in occurrences],
        f"{path}.asset_occurrences",
        "OCCURRENCE_ORDER_SEQUENCE",
        issues,
    )
    occurrence_ids: set[str] = set()
    for occurrence_index, occurrence in enumerate(occurrences):
        occurrence_path = f"{path}.asset_occurrences[{occurrence_index}]"
        _validate_occurrence(
            occurrence,
            occurrence_path,
            actual_page_id,
            assets,
            width,
            height,
            seen_ids,
            occurrence_ids,
            issues,
        )

    blocks = page.get("blocks", [])
    _validate_orders(
        [item.get("block_order") for item in blocks],
        f"{path}.blocks",
        "BLOCK_ORDER_SEQUENCE",
        issues,
    )
    for block_index, block in enumerate(blocks):
        _validate_block(
            block,
            f"{path}.blocks[{block_index}]",
            actual_page_id,
            width,
            height,
            occurrence_ids,
            seen_ids,
            issues,
        )


def _validate_occurrence(
    occurrence: Mapping[str, Any],
    path: str,
    parent_page_id: str,
    assets: Mapping[str, Mapping[str, Any]],
    width: float,
    height: float,
    seen_ids: set[str],
    occurrence_ids: set[str],
    issues: list[ValidationIssue],
) -> None:
    referenced_asset_id = occurrence.get("asset_id")
    if referenced_asset_id not in assets:
        _add(issues, "ASSET_NOT_FOUND", f"{path}.asset_id", "must reference document.assets")
    try:
        expected_id = asset_occurrence_id(
            parent_page_id,
            referenced_asset_id,
            occurrence.get("occurrence_order"),
        )
    except (TypeError, ValueError):
        expected_id = None
    actual_id = occurrence.get("asset_occurrence_id")
    if expected_id is not None and actual_id != expected_id:
        _add(issues, "OCCURRENCE_ID_MISMATCH", f"{path}.asset_occurrence_id", f"expected {expected_id}")
    _register_id(actual_id, f"{path}.asset_occurrence_id", seen_ids, issues)
    occurrence_ids.add(actual_id)
    _validate_bbox(occurrence.get("bbox"), width, height, f"{path}.bbox", issues)


def _validate_block(
    block: Mapping[str, Any],
    path: str,
    parent_page_id: str,
    width: float,
    height: float,
    occurrence_ids: set[str],
    seen_ids: set[str],
    issues: list[ValidationIssue],
) -> None:
    actual_id = block.get("block_id")
    try:
        expected_id = block_id(parent_page_id, block.get("block_order"))
    except (TypeError, ValueError):
        expected_id = None
    if expected_id is not None and actual_id != expected_id:
        _add(issues, "BLOCK_ID_MISMATCH", f"{path}.block_id", f"expected {expected_id}")
    _register_id(actual_id, f"{path}.block_id", seen_ids, issues)
    _validate_bbox(block.get("bbox"), width, height, f"{path}.bbox", issues)

    for reference in block.get("asset_occurrence_ids", []):
        if reference not in occurrence_ids:
            _add(
                issues,
                "OCCURRENCE_NOT_FOUND",
                f"{path}.asset_occurrence_ids",
                f"unknown occurrence {reference}",
            )

    lines = block.get("lines", [])
    _validate_orders(
        [item.get("line_order") for item in lines],
        f"{path}.lines",
        "LINE_ORDER_SEQUENCE",
        issues,
    )
    for line_index, line in enumerate(lines):
        _validate_line(
            line,
            f"{path}.lines[{line_index}]",
            actual_id,
            width,
            height,
            seen_ids,
            issues,
        )


def _validate_line(
    line: Mapping[str, Any],
    path: str,
    parent_block_id: str,
    width: float,
    height: float,
    seen_ids: set[str],
    issues: list[ValidationIssue],
) -> None:
    actual_id = line.get("line_id")
    try:
        expected_id = line_id(parent_block_id, line.get("line_order"))
    except (TypeError, ValueError):
        expected_id = None
    if expected_id is not None and actual_id != expected_id:
        _add(issues, "LINE_ID_MISMATCH", f"{path}.line_id", f"expected {expected_id}")
    _register_id(actual_id, f"{path}.line_id", seen_ids, issues)
    _validate_bbox(line.get("bbox"), width, height, f"{path}.bbox", issues)

    spans = line.get("spans", [])
    _validate_orders(
        [item.get("span_order") for item in spans],
        f"{path}.spans",
        "SPAN_ORDER_SEQUENCE",
        issues,
    )
    for span_index, span in enumerate(spans):
        span_path = f"{path}.spans[{span_index}]"
        actual_span_id = span.get("span_id")
        try:
            expected_span_id = span_id(actual_id, span.get("span_order"))
        except (TypeError, ValueError):
            expected_span_id = None
        if expected_span_id is not None and actual_span_id != expected_span_id:
            _add(issues, "SPAN_ID_MISMATCH", f"{span_path}.span_id", f"expected {expected_span_id}")
        _register_id(actual_span_id, f"{span_path}.span_id", seen_ids, issues)
        _validate_bbox(span.get("bbox"), width, height, f"{span_path}.bbox", issues)


def _validate_bbox(
    bbox: Sequence[float],
    width: float,
    height: float,
    path: str,
    issues: list[ValidationIssue],
) -> None:
    if not isinstance(bbox, Sequence) or isinstance(bbox, (str, bytes)) or len(bbox) != 4:
        return  # La forma corresponde a JSON Schema.
    x0, y0, x1, y1 = bbox
    if not (0 <= x0 <= x1 <= width and 0 <= y0 <= y1 <= height):
        _add(issues, "BBOX_OUT_OF_PAGE", path, f"must fit inside page {width}x{height}")


def _validate_orders(
    values: Sequence[Any],
    path: str,
    code: str,
    issues: list[ValidationIssue],
) -> None:
    expected = list(range(1, len(values) + 1))
    if list(values) != expected:
        _add(issues, code, path, f"expected consecutive order {expected}, received {list(values)}")


def _validate_relative_asset_path(value: Any, path: str, issues: list[ValidationIssue]) -> None:
    if not isinstance(value, str):
        return
    candidate = PurePosixPath(value.replace("\\", "/"))
    if candidate.is_absolute() or ".." in candidate.parts:
        _add(issues, "UNSAFE_ASSET_PATH", path, "must be a relative path without '..'")


def _register_id(
    value: Any,
    path: str,
    seen_ids: set[str],
    issues: list[ValidationIssue],
) -> None:
    if not isinstance(value, str):
        return
    if value in seen_ids:
        _add(issues, "DUPLICATE_ENTITY_ID", path, "must be unique in the document")
    seen_ids.add(value)


def _add(issues: list[ValidationIssue], code: str, path: str, message: str) -> None:
    issues.append(ValidationIssue(code, path, message))
