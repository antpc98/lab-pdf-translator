"""Pruebas unitarias de relaciones que JSON Schema no puede expresar.

Bitácora: 2026-08-30 - Identidad, secuencias, geometría y recursos.
"""

from __future__ import annotations

from copy import deepcopy

import pytest

from lab_pdf_translator.validation.issues import DatasetValidationError
from lab_pdf_translator.validation.semantic import (
    require_valid_semantics,
    validate_semantics,
)


def _codes(document: dict) -> set[str]:
    return {issue.code for issue in validate_semantics(document)}


def test_representative_document_is_semantically_valid(
    representative_document: dict,
) -> None:
    assert validate_semantics(representative_document) == ()
    require_valid_semantics(representative_document)


def test_page_count_must_match_physical_pages(representative_document: dict) -> None:
    document = deepcopy(representative_document)
    document["page_count"] = 2
    assert "PAGE_COUNT_MISMATCH" in _codes(document)


def test_document_and_descendant_ids_are_recomputed(
    representative_document: dict,
) -> None:
    document = deepcopy(representative_document)
    document["document_id"] = "00000000-0000-5000-8000-000000000000"
    codes = _codes(document)
    assert "DOCUMENT_ID_MISMATCH" in codes
    assert "PAGE_ID_MISMATCH" in codes


def test_orders_must_be_consecutive(representative_document: dict) -> None:
    document = deepcopy(representative_document)
    document["pages"][0]["blocks"][0]["block_order"] = 2
    codes = _codes(document)
    assert "BLOCK_ORDER_SEQUENCE" in codes
    assert "BLOCK_ID_MISMATCH" in codes


def test_bbox_must_fit_inside_page(representative_document: dict) -> None:
    document = deepcopy(representative_document)
    document["pages"][0]["blocks"][0]["bbox"] = [0, 0, 900, 900]
    assert "BBOX_OUT_OF_PAGE" in _codes(document)


def test_assets_require_content_identity_and_safe_paths(
    representative_document: dict,
) -> None:
    document = deepcopy(representative_document)
    document["assets"][0]["asset_id"] = "sha256:" + ("0" * 64)
    document["assets"][0]["path"] = "../outside.png"
    codes = _codes(document)
    assert "ASSET_ID_MISMATCH" in codes
    assert "UNSAFE_ASSET_PATH" in codes


def test_occurrences_must_reference_registered_assets(
    representative_document: dict,
) -> None:
    document = deepcopy(representative_document)
    occurrence = document["pages"][0]["asset_occurrences"][0]
    occurrence["asset_id"] = "sha256:" + ("f" * 64)
    codes = _codes(document)
    assert "ASSET_NOT_FOUND" in codes
    assert "OCCURRENCE_ID_MISMATCH" in codes


def test_blocks_must_reference_page_occurrences(representative_document: dict) -> None:
    document = deepcopy(representative_document)
    document["pages"][0]["blocks"][0]["asset_occurrence_ids"] = [
        "00000000-0000-5000-8000-000000000000"
    ]
    assert "OCCURRENCE_NOT_FOUND" in _codes(document)


def test_all_entity_ids_must_be_unique(representative_document: dict) -> None:
    document = deepcopy(representative_document)
    block = document["pages"][0]["blocks"][0]
    block["lines"][0]["spans"][0]["span_id"] = block["block_id"]
    codes = _codes(document)
    assert "DUPLICATE_ENTITY_ID" in codes
    assert "SPAN_ID_MISMATCH" in codes


def test_require_valid_semantics_raises_aggregated_error(
    representative_document: dict,
) -> None:
    document = deepcopy(representative_document)
    document["page_count"] = 99
    with pytest.raises(DatasetValidationError, match="PAGE_COUNT_MISMATCH"):
        require_valid_semantics(document)


@pytest.mark.parametrize(
    ("location", "order_field", "code"),
    [
        (("asset_occurrences", 0), "occurrence_order", "OCCURRENCE_ORDER_SEQUENCE"),
        (("blocks", 0, "lines", 0), "line_order", "LINE_ORDER_SEQUENCE"),
        (("blocks", 0, "lines", 0, "spans", 0), "span_order", "SPAN_ORDER_SEQUENCE"),
    ],
)
def test_nested_orders_must_be_consecutive(
    representative_document: dict,
    location: tuple,
    order_field: str,
    code: str,
) -> None:
    document = deepcopy(representative_document)
    value = document["pages"][0]
    for component in location:
        value = value[component]
    value[order_field] = 2
    assert code in _codes(document)


@pytest.mark.parametrize(
    "location",
    [
        ("asset_occurrences", 0),
        ("blocks", 0, "lines", 0),
        ("blocks", 0, "lines", 0, "spans", 0),
    ],
)
def test_all_nested_geometries_are_checked(
    representative_document: dict,
    location: tuple,
) -> None:
    document = deepcopy(representative_document)
    value = document["pages"][0]
    for component in location:
        value = value[component]
    value["bbox"] = [0, 0, 999, 999]
    assert "BBOX_OUT_OF_PAGE" in _codes(document)


def test_page_numbers_must_start_at_one(representative_document: dict) -> None:
    document = deepcopy(representative_document)
    document["pages"][0]["page_number"] = 2
    codes = _codes(document)
    assert "PAGE_NUMBER_SEQUENCE" in codes
    assert "PAGE_ID_MISMATCH" in codes


def test_asset_ids_must_be_unique(representative_document: dict) -> None:
    document = deepcopy(representative_document)
    document["assets"].append(deepcopy(document["assets"][0]))
    assert "DUPLICATE_ASSET_ID" in _codes(document)
